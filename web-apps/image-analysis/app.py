import base64
import gradio as gr
import logging
import requests
import utils

from typing import List, Dict
from io import BytesIO
from PIL import Image
from pydantic import BaseModel, ConfigDict
from urllib.parse import urljoin


log = utils.get_logger()


class PromptExample(BaseModel):
    image_url: str
    prompt: str


class AppSettings(BaseModel):
    # Basic config
    host_address: str
    backend_url: str
    model_name: str
    page_title: str
    page_description: str
    examples: List[PromptExample]
    llm_params: utils.LLMParams | None
    # Theme customisation
    theme_params: Dict[str, str | list]
    theme_params_extended: Dict[str, str]
    css_overrides: str | None
    custom_javascript: str | None
    # Error on typos and suppress warnings for fields with 'model_' prefix
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")


settings = AppSettings(**utils.load_settings())
log.info(settings)


# TODO: Rewrite this to stream output?
def analyze_image(image_url, prompt):
    try:
        # Download the image
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))

        # Convert image to base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # Prepare the payload for the vision model
        payload = {
            "model": settings.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_str}"},
                        },
                    ],
                }
            ],
            **{k: v for k, v in settings.llm_params if k != "top_k" and v is not None},
        }
        if settings.llm_params.top_k:
            payload["extra_body"] = {
                "top_k": settings.llm_params.top_k,
            }
        log.debug("Request payload: %s", payload)

        # Make the API call to the vision model
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            urljoin(settings.backend_url, "/v1/chat/completions"),
            json=payload,
            headers=headers,
        )
        log.debug("Request payload: %s", payload)
        try:
            response.raise_for_status()
        except Exception as e:
            log.debug(
                "Received HTTP %s response with content: %s",
                response.status_code,
                response.json(),
            )
            raise e

        # Extract and return the model's response
        result = response.json()
        return image, result["choices"][0]["message"]["content"]

    except Exception as e:
        return f"An error occurred: {str(e)}"


# UI theming
theme = gr.themes.Default(**settings.theme_params)
theme.set(**settings.theme_params_extended)

# Set up the Gradio interface
app = gr.Interface(
    fn=analyze_image,
    inputs=[
        gr.Textbox(label="Image URL"),
        gr.Textbox(label="Prompt/Question", elem_id="prompt", scale=2),
    ],
    outputs=[gr.Image(label="Image"), gr.Textbox(label="Results")],
    title=settings.page_title,
    description=settings.page_description,
    examples=[[ex.image_url, ex.prompt] for ex in settings.examples],
    theme=theme,
    css=settings.css_overrides,
    js=settings.custom_javascript,
    analytics_enabled=False,
)

# Launch the interface
app.queue(default_concurrency_limit=10).launch(server_name=settings.host_address)
