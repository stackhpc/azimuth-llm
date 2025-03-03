import openai
import utils
import gradio as gr

from urllib.parse import urljoin
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing import Dict
from pydantic import BaseModel, ConfigDict

log = utils.get_logger()


class AppSettings(BaseModel):
    # Basic config
    host_address: str
    backend_url: str
    model_name: str
    model_instruction: str
    page_title: str
    llm_params: utils.LLMParams
    # Theme customisation
    theme_params: Dict[str, str | list]
    theme_params_extended: Dict[str, str]
    css_overrides: str | None
    custom_javascript: str | None
    # Error on typos and suppress warnings for fields with 'model_' prefix
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")


settings = AppSettings(**utils.load_settings())
log.info(settings)

backend_url = str(settings.backend_url)
backend_health_endpoint = urljoin(backend_url, "/health")
BACKEND_INITIALISED = False

# Some models disallow 'system' role's their conversation history by raising errors in their chat prompt template, e.g. see
# https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/blob/cf47bb3e18fe41a5351bc36eef76e9c900847c89/tokenizer_config.json#L42
# Detecting this ahead of time is difficult so for now we use a global variable which stores whether the API has
# responded with a HTTP 400 error and formats all subsequent request to avoid using a system role.
INCLUDE_SYSTEM_PROMPT = True


class PossibleSystemPromptException(Exception):
    pass


llm = ChatOpenAI(
    base_url=urljoin(backend_url, "v1"),
    model=settings.model_name,
    openai_api_key="required-but-not-used",
    temperature=settings.llm_params.temperature,
    max_tokens=settings.llm_params.max_tokens,
    top_p=settings.llm_params.top_p,
    frequency_penalty=settings.llm_params.frequency_penalty,
    presence_penalty=settings.llm_params.presence_penalty,
    extra_body={
        "top_k": settings.llm_params.top_k,
    },
    streaming=True,
)

def inference(latest_message, history):
    # Allow mutating global variable
    global BACKEND_INITIALISED
    log.debug("Inference request received with history: %s", history)

    try:
        context = []
        if INCLUDE_SYSTEM_PROMPT:
            context.append(SystemMessage(content=settings.model_instruction))
        else:
            # Mimic system prompt by prepending it to first human message
            history[0]['content'] = f"{settings.model_instruction}\n\n{history[0]['content']}"

        for message in history:
            role = message['role']
            content = message['content']
            if role == "user":
                context.append(HumanMessage(content=content))
            else:
                if role != "assistant":
                    log.warn(f"Message role {role} converted to 'assistant'")
                context.append(AIMessage(content=(content or "")))
        context.append(HumanMessage(content=latest_message))

        log.debug("Chat context: %s", context)

        response = ""
        thinking = False

        for chunk in llm.stream(context):
            # If this is our first successful response from the backend
            # then update the status variable to allow future error messages
            # to be more informative
            if not BACKEND_INITIALISED and len(response) > 0:
                BACKEND_INITIALISED = True

            # The "think" tags mark the chatbot's reasoning. Remove the content
            # and replace with "Thinking..." until the closing tag is found.
            content = chunk.content
            if '<think>' in content or thinking:
                thinking = True
                response = "Thinking..."
                if '</think>' in content:
                    thinking = False
                    response = ""
            else:
                response += content
            yield response

    # Handle any API errors here. See OpenAI Python client for possible error responses
    # https://github.com/openai/openai-python/tree/e8e5a0dc7ccf2db19d7f81991ee0987f9c3ae375?tab=readme-ov-file#handling-errors

    except openai.BadRequestError as err:
        log.error("Received BadRequestError from backend API: %s", err)
        message = err.response.json()["message"]
        if INCLUDE_SYSTEM_PROMPT:
            raise PossibleSystemPromptException()
        else:
            # In this case we've already tried without system prompt and still hit a bad request error so something else must be wrong
            ui_message = f"API Error received. This usually means the chosen LLM uses an incompatible prompt format. Error message was: {message}"
            raise gr.Error(ui_message)

    except openai.APIConnectionError as err:
        log.info(err)
        if not BACKEND_INITIALISED:
            log.info("Backend API not yet ready")
            gr.Info(
                "Backend not ready - model may still be initialising - please try again later."
            )
        else:
            log.error("Failed to connect to backend API: %s", err)
            gr.Warning("Failed to connect to backend API.")

    except openai.InternalServerError as err:
        gr.Warning(
            "Internal server error encountered in backend API - see API logs for details."
        )

    # Catch-all for unexpected exceptions
    except Exception as err:
        log.error("Unexpected error during inference: %s", err)
        raise gr.Error("Unexpected error encountered - see logs for details.")


def inference_wrapper(*args):
    """
    Simple wrapper round the `inference` function which catches certain predictable errors
    such as invalid prompt formats and attempts to mitigate them automatically.
    """
    # Allow mutating global variable
    global INCLUDE_SYSTEM_PROMPT
    try:
        for chunk in inference(*args):
            yield chunk
    except PossibleSystemPromptException:
        log.warning("Disabling system prompt and retrying previous request")
        INCLUDE_SYSTEM_PROMPT = False
        for chunk in inference(*args):
            yield chunk


# UI theming
theme = gr.themes.Default(**settings.theme_params)
theme.set(**settings.theme_params_extended)

with gr.Blocks(
    fill_height=True,
    theme=theme,
    css=settings.css_overrides,
    js=settings.custom_javascript,
    title=settings.page_title,
) as demo:
    gr.Markdown('# ' + settings.page_title)
    gr.ChatInterface(
        inference_wrapper,
        type="messages",
        analytics_enabled=False,
        chatbot=gr.Chatbot(
            show_copy_button=True,
            height="75vh",
            resizable=True,
            sanitize_html=True,
            ),
    )


if __name__ == "__main__":
    log.debug("Gradio chat interface config: %s", demo.config)
    demo.queue(
        default_concurrency_limit=10,
    ).launch(server_name=settings.host_address)
