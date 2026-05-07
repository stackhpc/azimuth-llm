"""Azimuth Omni: ttt-first UI with optional tts/tti backends."""

import base64
import gradio as gr
import httpx
import io
import tempfile
import threading
import time
import utils

from datetime import date
from openai import OpenAI
from pathlib import Path
from PIL import Image
from pydantic import BaseModel, ConfigDict
from scipy.io import wavfile
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

log = utils.get_logger()
log.info(f"Gradio version: {gr.__version__}")


# Param classes hold the known UI defaults. Extra keys in a backend's params
# are kept and forwarded to the backend via the OpenAI SDK extra_body.


class ChatParams(BaseModel):
    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    model_config = ConfigDict(extra="allow")


class TTSParams(BaseModel):
    voice: str = "casual_male"
    response_format: str = "wav"
    model_config = ConfigDict(extra="allow")


class ImageGenParams(BaseModel):
    size: str = "1024x1024"
    style: Optional[str] = None
    quality: Optional[str] = None
    model_config = ConfigDict(extra="allow")


# Per-backend UI config: dropdown choices and slider ranges. All optional.


class ChatUI(BaseModel):
    model_config = ConfigDict(extra="allow")


class TTSUI(BaseModel):
    voice_choices: Optional[List[str]] = None
    format_choices: List[str] = ["wav", "mp3", "ogg", "aac", "flac"]
    model_config = ConfigDict(extra="allow")


class ImageUI(BaseModel):
    size_choices: List[str] = [
        "1024x1024",
        "1024x1792",
        "1792x1024",
        "512x512",
        "256x256",
    ]
    style_choices: Optional[List[str]] = None
    quality_choices: Optional[List[str]] = None
    show_negative_prompt: bool = True
    model_config = ConfigDict(extra="allow")


class BackendConfig(BaseModel):
    backend_url: str
    model_name: str
    system_prompt: Optional[str] = None
    params: Dict[str, Any] = {}
    ui: Dict[str, Any] = {}
    # OpenAI client request timeout (seconds). Falls back to AppConfig.
    request_timeout_s: Optional[float] = None
    model_config = ConfigDict(extra="allow")


class AppConfig(BaseModel):
    probe_timeout_s: float = 2.0
    probe_interval_s: float = 10.0
    concurrency_limit: int = 5
    # Default OpenAI client timeout (seconds) for inference requests.
    request_timeout_s: float = 1800.0
    model_config = ConfigDict(extra="allow")


class AppSettings(BaseModel):
    host_address: str = "0.0.0.0"
    page_title: str = "Omni Interface"
    page_description: str = ""
    app: AppConfig = AppConfig()
    ttt: Optional[BackendConfig] = None
    tts: Optional[BackendConfig] = None
    tti: Optional[BackendConfig] = None
    theme_params: Dict[str, Any] = {}
    theme_params_extended: Dict[str, Any] = {}
    css_overrides: Optional[str] = None
    custom_javascript: Optional[str] = None
    model_config = ConfigDict(protected_namespaces=(), extra="allow")


def load_settings() -> dict:
    """Merge defaults.yml with overrides (k8s mount path, then local fallback)."""
    defaults = utils.load_yaml("./defaults.yml")
    for candidate in ("/etc/web-app/overrides.yml", "./overrides.yml"):
        if Path(candidate).exists():
            return {**defaults, **utils.load_yaml(candidate)}
    return defaults


settings = AppSettings(**load_settings())


BACKEND_NAMES = ("ttt", "tts", "tti")

clients: Dict[str, OpenAI] = {}
probe_urls: Dict[str, str] = {}
for name in BACKEND_NAMES:
    cfg: Optional[BackendConfig] = getattr(settings, name)
    if cfg is None:
        continue
    base = cfg.backend_url.rstrip("/") + "/"
    timeout_s = (
        cfg.request_timeout_s
        if cfg.request_timeout_s is not None
        else settings.app.request_timeout_s
    )
    clients[name] = OpenAI(
        base_url=urljoin(base, "v1"),
        api_key="not-needed",
        timeout=timeout_s,
    )
    probe_urls[name] = urljoin(base, "v1/models")
    log.info(f"  {name}: client request_timeout_s={timeout_s}")

enabled = list(clients.keys())
log.info(f"Enabled backends: {enabled}")
if not enabled:
    raise RuntimeError(
        f"No backends configured. Set at least one of: {', '.join(BACKEND_NAMES)}"
    )


# A background thread probes GET /v1/models for every backend and writes the
# results to `health`. UI refresh and inference guards read from it.

PROBE_TIMEOUT_S = settings.app.probe_timeout_s
PROBE_INTERVAL_S = settings.app.probe_interval_s

_probe_http = httpx.Client(timeout=PROBE_TIMEOUT_S)
health: Dict[str, bool] = {name: False for name in enabled}


def _probe_once() -> None:
    for name in enabled:
        try:
            health[name] = _probe_http.get(probe_urls[name]).is_success
        except httpx.HTTPError as e:
            health[name] = False
            log.debug(f"Health probe failed for {name}: {e}")


def _probe_loop() -> None:
    while True:
        time.sleep(PROBE_INTERVAL_S)
        _probe_once()


# Prime synchronously so the first page load sees real values.
_probe_once()
threading.Thread(target=_probe_loop, name="health-probe", daemon=True).start()


def _status_markdown(name: str) -> str:
    url = getattr(settings, name).backend_url
    if health[name]:
        return f"**Status:** reachable - `{url}`"
    return (
        f"**Status:** unreachable - `{url}` "
        f"(retrying every {int(PROBE_INTERVAL_S)}s; inputs disabled)"
    )


def file_to_base64(file_path: str) -> tuple[str, str]:
    """Convert a file to base64, return (data_uri, mime_type)."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
    }
    mime_type = mime_types.get(suffix, "application/octet-stream")
    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime_type};base64,{data}", mime_type


def build_message_content(text: str, files: List[str]) -> List[Dict]:
    content = []
    if text:
        content.append({"type": "text", "text": text})
    for fp in files:
        uri, mt = file_to_base64(fp)
        if mt.startswith("image/"):
            content.append({"type": "image_url", "image_url": {"url": uri}})
        elif mt.startswith("audio/"):
            content.append(
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": uri.split(",")[1],
                        "format": mt.split("/")[1],
                    },
                }
            )
        elif mt.startswith("video/"):
            content.append({"type": "video_url", "video_url": {"url": uri}})
    return content or [{"type": "text", "text": ""}]


_CHAT_NATIVE_KEYS = {"max_tokens", "temperature", "top_p"}


def _split_native(params: Dict[str, Any], native: set) -> tuple[Dict, Dict]:
    """Partition params into (SDK-native kwargs, extra_body for the rest)."""
    native_kwargs = {k: v for k, v in params.items() if k in native}
    extra = {k: v for k, v in params.items() if k not in native}
    return native_kwargs, extra


def chat_inference(message, history):
    cfg = settings.ttt
    client = clients["ttt"]
    raw_params = {**ChatParams().model_dump(), **cfg.params}
    native_kwargs, extra_body = _split_native(raw_params, _CHAT_NATIVE_KEYS)

    if not health["ttt"]:
        yield (
            "Chat backend is currently unreachable. The status banner above "
            "will update once it comes back online."
        )
        return

    try:
        messages = []
        if cfg.system_prompt:
            sp = cfg.system_prompt.replace("{date}", str(date.today()))
            messages.append({"role": "system", "content": sp})

        for msg in history:
            content = msg.get("content", "")
            if isinstance(content, dict) and "path" in content:
                content = build_message_content("", [content["path"]])
            elif not isinstance(content, (str, list)):
                continue
            messages.append({"role": msg.get("role", "user"), "content": content})

        if isinstance(message, dict):
            text = message.get("text", "") or ""
            files = message.get("files", [])
            content = build_message_content(text, files)
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": str(message)})

        create_kwargs: Dict[str, Any] = dict(
            model=cfg.model_name,
            messages=messages,
            stream=True,
            **native_kwargs,
        )
        if extra_body:
            create_kwargs["extra_body"] = extra_body
        stream = client.chat.completions.create(**create_kwargs)

        response = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                response += chunk.choices[0].delta.content
                yield response

    except Exception as e:
        log.error(f"Chat error: {e}")
        yield f"Error: {e}"


_TTS_NATIVE_KEYS = {"voice", "response_format", "speed"}


def tts_inference(text: str, voice: str, response_format: str):
    cfg = settings.tts
    client = clients["tts"]

    if not health["tts"]:
        raise gr.Error("TTS backend is currently unreachable.")

    raw_params = {**TTSParams().model_dump(), **cfg.params}
    raw_params["response_format"] = response_format
    if voice:
        raw_params["voice"] = voice
    else:
        raw_params.pop("voice", None)
    native_kwargs, extra_body = _split_native(raw_params, _TTS_NATIVE_KEYS)

    try:
        create_kwargs: Dict[str, Any] = dict(
            model=cfg.model_name,
            input=text,
            **native_kwargs,
        )
        if extra_body:
            create_kwargs["extra_body"] = extra_body
        response = client.audio.speech.create(**create_kwargs)
        audio_bytes = response.read()

        if response_format == "wav":
            sr, audio = wavfile.read(io.BytesIO(audio_bytes))
            return (sr, audio)
        with tempfile.NamedTemporaryFile(
            suffix=f".{response_format}", delete=False
        ) as f:
            f.write(audio_bytes)
            return f.name

    except Exception as e:
        log.error(f"TTS error: {e}")
        raise gr.Error(f"TTS error: {e}")


_IMAGE_NATIVE_KEYS = {"size", "style", "quality", "n", "response_format"}


def image_inference(
    prompt: str,
    negative_prompt: Optional[str] = None,
    size: Optional[str] = None,
    style: Optional[str] = None,
    quality: Optional[str] = None,
):
    cfg = settings.tti
    client = clients["tti"]

    if not health["tti"]:
        raise gr.Error("Image backend is currently unreachable.")

    raw_params: Dict[str, Any] = {**cfg.params}
    # Live UI values override config; None/empty means don't send.
    for key, val in (("size", size), ("style", style), ("quality", quality)):
        if val:
            raw_params[key] = val
    raw_params.setdefault("response_format", "b64_json")
    if negative_prompt:
        raw_params["negative_prompt"] = negative_prompt

    native_kwargs, extra_body = _split_native(raw_params, _IMAGE_NATIVE_KEYS)

    try:
        create_kwargs: Dict[str, Any] = dict(
            model=cfg.model_name,
            prompt=prompt,
            **native_kwargs,
        )
        if extra_body:
            create_kwargs["extra_body"] = extra_body
        response = client.images.generate(**create_kwargs)
        if response.data and response.data[0].b64_json:
            return Image.open(io.BytesIO(base64.b64decode(response.data[0].b64_json)))
        raise gr.Error("No image data received from model")

    except gr.Error:
        raise
    except Exception as e:
        log.error(f"Image generation error: {e}")
        raise gr.Error(f"Image generation error: {e}")


theme = gr.themes.Default(**settings.theme_params)
if settings.theme_params_extended:
    theme.set(**settings.theme_params_extended)

blocks_kwargs = {
    "fill_height": True,
    "title": settings.page_title,
    "theme": theme,
    "css": settings.css_overrides,
    "js": settings.custom_javascript,
}
launch_kwargs = {"server_name": settings.host_address}


with gr.Blocks(**blocks_kwargs) as demo:
    gr.Markdown(f"# {settings.page_title}")
    if settings.page_description:
        gr.Markdown(settings.page_description)

    # {backend_name: (status_markdown, [widgets to toggle when unreachable])}
    health_widgets: Dict[str, tuple] = {}

    with gr.Tabs():
        if settings.ttt:
            with gr.Tab("Chat"):
                gr.Markdown(f"**Model:** `{settings.ttt.model_name}`")
                chat_status = gr.Markdown(_status_markdown("ttt"))

                chatbot = gr.Chatbot(
                    type="messages",
                    height="65vh",
                    resizable=True,
                    sanitize_html=True,
                    autoscroll=True,
                    show_copy_button=True,
                    allow_tags=False,
                    latex_delimiters=[
                        {"left": "$$", "right": "$$", "display": True},
                        {"left": "$", "right": "$", "display": False},
                    ],
                )
                textbox = gr.MultimodalTextbox(
                    file_types=["image", "audio", "video"],
                    file_count="multiple",
                    placeholder="Type a message or upload files...",
                    show_label=False,
                )
                gr.ChatInterface(
                    fn=chat_inference,
                    type="messages",
                    multimodal=True,
                    chatbot=chatbot,
                    textbox=textbox,
                    analytics_enabled=False,
                )
                health_widgets["ttt"] = (chat_status, [textbox])

        if settings.tts:
            tts_defaults = TTSParams(**settings.tts.params)
            tts_ui = TTSUI(**(settings.tts.ui or {}))

            with gr.Tab("Text-to-Speech"):
                gr.Markdown(f"**Model:** `{settings.tts.model_name}`")
                tts_status = gr.Markdown(_status_markdown("tts"))

                with gr.Row():
                    with gr.Column(scale=2):
                        tts_input = gr.Textbox(
                            label="Text to Speak",
                            placeholder="Enter the text you want to convert to speech...",
                            lines=5,
                        )
                        tts_output = gr.Audio(
                            label="Generated Audio",
                            show_download_button=True,
                        )
                    with gr.Column(scale=1):
                        if tts_ui.voice_choices:
                            tts_voice = gr.Dropdown(
                                choices=tts_ui.voice_choices,
                                value=(
                                    tts_defaults.voice
                                    if tts_defaults.voice in tts_ui.voice_choices
                                    else tts_ui.voice_choices[0]
                                ),
                                label="Voice",
                            )
                        else:
                            tts_voice = gr.Textbox(
                                value=tts_defaults.voice,
                                label="Voice",
                                info="Voice name supported by the model",
                            )
                        tts_format = gr.Dropdown(
                            choices=tts_ui.format_choices,
                            value=(
                                tts_defaults.response_format
                                if tts_defaults.response_format in tts_ui.format_choices
                                else tts_ui.format_choices[0]
                            ),
                            label="Format",
                        )
                        tts_btn = gr.Button("Generate Speech", variant="primary")

                tts_btn.click(
                    tts_inference, [tts_input, tts_voice, tts_format], tts_output
                )
                health_widgets["tts"] = (
                    tts_status,
                    [tts_input, tts_voice, tts_format, tts_btn],
                )

        if settings.tti:
            img_defaults = ImageGenParams(**settings.tti.params)
            img_ui = ImageUI(**(settings.tti.ui or {}))

            with gr.Tab("Image Generation"):
                gr.Markdown(f"**Model:** `{settings.tti.model_name}`")
                image_status = gr.Markdown(_status_markdown("tti"))

                with gr.Row():
                    with gr.Column(scale=2):
                        img_prompt = gr.Textbox(
                            label="Prompt", placeholder="Describe the image...", lines=3
                        )
                        img_negative = gr.Textbox(
                            label="Negative Prompt (optional)",
                            lines=2,
                            visible=img_ui.show_negative_prompt,
                        )
                        img_output = gr.Image(label="Generated Image", height=512)
                    with gr.Column(scale=1):
                        img_size = gr.Dropdown(
                            choices=img_ui.size_choices,
                            value=(
                                img_defaults.size
                                if img_defaults.size in img_ui.size_choices
                                else (
                                    img_ui.size_choices[0]
                                    if img_ui.size_choices
                                    else None
                                )
                            ),
                            label="Size",
                        )
                        # style/quality hidden unless configured (DALL-E-3-specific).
                        img_style = gr.Dropdown(
                            choices=img_ui.style_choices or [],
                            value=img_defaults.style,
                            label="Style",
                            visible=bool(img_ui.style_choices),
                        )
                        img_quality = gr.Dropdown(
                            choices=img_ui.quality_choices or [],
                            value=img_defaults.quality,
                            label="Quality",
                            visible=bool(img_ui.quality_choices),
                        )
                        img_btn = gr.Button("Generate Image", variant="primary")

                img_btn.click(
                    image_inference,
                    [img_prompt, img_negative, img_size, img_style, img_quality],
                    img_output,
                )
                health_widgets["tti"] = (
                    image_status,
                    [
                        img_prompt,
                        img_negative,
                        img_size,
                        img_style,
                        img_quality,
                        img_btn,
                    ],
                )

    # Order must match refresh_health: status_md then inputs, per backend.
    health_outputs = [
        w
        for name in enabled
        for w in (health_widgets[name][0], *health_widgets[name][1])
    ]

    def refresh_health() -> List[Any]:
        updates: List[Any] = []
        for name in enabled:
            _, inputs = health_widgets[name]
            updates.append(gr.update(value=_status_markdown(name)))
            updates.extend(gr.update(interactive=health[name]) for _ in inputs)
        return updates

    # Timer is per-session and only drives the UI; probing is global.
    demo.load(refresh_health, inputs=None, outputs=health_outputs)
    gr.Timer(PROBE_INTERVAL_S).tick(refresh_health, inputs=None, outputs=health_outputs)


if __name__ == "__main__":
    for name in enabled:
        cfg = getattr(settings, name)
        log.info(f"  {name}: model={cfg.model_name} url={cfg.backend_url}")
    demo.queue(default_concurrency_limit=settings.app.concurrency_limit).launch(
        **launch_kwargs
    )
