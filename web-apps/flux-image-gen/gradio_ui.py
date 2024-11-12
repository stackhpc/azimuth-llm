import io
import os
import httpx
import uuid
import pathlib
import yaml

import gradio as gr
from pydantic import BaseModel, HttpUrl
from PIL import Image, ExifTags
from typing import List
from urllib.parse import urljoin


class Model(BaseModel):
    name: str
    address: HttpUrl

class AppSettings(BaseModel):
    models: List[Model]
    example_prompt: str = "Yoda riding a skateboard."
    title = "Flux Image Generation Demo"



settings_path = pathlib.Path("/etc/gradio-app/gradio_config.yaml")
if not settings_path.exists():
    print("No settings overrides found at", settings_path)
    settings_path = "./gradio_config.yaml"
print("Using settings from", settings_path)
with open(settings_path, "r") as file:
    settings = AppSettings(**yaml.safe_load(file))
print("App config:", settings.model_dump())

MODELS = {m.name: m.address for m in settings.models}
MODEL_NAMES = list(MODELS.keys())

# Disable analytics for GDPR compliance
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

def save_image(model_name: str, prompt: str, seed: int, add_sampling_metadata: bool, image: Image.Image):
    filename = f"output/gradio/{uuid.uuid4()}.jpg"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    exif_data = Image.Exif()
    exif_data[ExifTags.Base.Software] = "AI generated;img2img;flux"
    exif_data[ExifTags.Base.Make] = "Black Forest Labs"
    exif_data[ExifTags.Base.Model] = model_name
    if add_sampling_metadata:
        exif_data[ExifTags.Base.ImageDescription] = prompt
    image.save(filename, format="jpeg", exif=exif_data, quality=95, subsampling=0)
    return filename


async def generate_image(
    model_name: str,
    width: int,
    height: int,
    num_steps: int,
    guidance: float,
    seed: int,
    prompt: str,
    add_sampling_metadata: bool,
):
    url = urljoin(str(MODELS[model_name]), "/generate")
    data = {
        "width": width,
        "height": height,
        "num_steps": num_steps,
        "guidance": guidance,
        "seed": seed,
        "prompt": prompt,
        "add_sampling_metadata": add_sampling_metadata,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(url, json=data)
        except httpx.ConnectError:
            raise gr.Error("Model backend unavailable")
        if response.status_code == 400:
            data = response.json()
            if "error" in data and "message" in data["error"]:
                message = data["error"]["message"]
                if "seed" in data["error"]:
                    message += f" (seed: {data['error']['seed']})"
                raise gr.Error(message)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            # Raise a generic error message to avoid leaking unwanted details
            # Admin should consult API logs for more info
            raise gr.Error(f"Backend error (HTTP {err.response.status_code})")
        image = Image.open(io.BytesIO(response.content))
        seed = response.headers.get("x-flux-seed", "unknown")
        filename = save_image(model_name, prompt, seed, add_sampling_metadata, image)

        return image, seed, filename, None

with gr.Blocks(title=settings.title) as demo:
    gr.Markdown(f"# {settings.title}")

    with gr.Row():
        with gr.Column():
            model = gr.Dropdown(MODEL_NAMES, value=MODEL_NAMES[0], label="Model", interactive=len(MODEL_NAMES) > 1)
            prompt = gr.Textbox(label="Prompt", value=settings.example_prompt)

            with gr.Accordion("Advanced Options", open=False):
                # TODO: Make min/max slide values configurable
                width = gr.Slider(128, 8192, 1360, step=16, label="Width")
                height = gr.Slider(128, 8192, 768, step=16, label="Height")
                num_steps = gr.Slider(1, 50, 4 if model.value == "flux-schnell" else 50, step=1, label="Number of steps")
                guidance = gr.Slider(1.0, 10.0, 3.5, step=0.1, label="Guidance", interactive=not model.value == "flux-schnell")
                seed = gr.Textbox("-1", label="Seed (-1 for random)")
                add_sampling_metadata = gr.Checkbox(label="Add sampling parameters to metadata?", value=True)

            generate_btn = gr.Button("Generate")

        with gr.Column():
            output_image = gr.Image(label="Generated Image")
            seed_output = gr.Textbox(label="Used Seed")
            warning_text = gr.Textbox(label="Warning", visible=False)
            download_btn = gr.File(label="Download full-resolution")

    generate_btn.click(
        fn=generate_image,
        inputs=[model, width, height, num_steps, guidance, seed, prompt, add_sampling_metadata],
        outputs=[output_image, seed_output, download_btn, warning_text],
    )
    demo.launch(enable_monitoring=False)
