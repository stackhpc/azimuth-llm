import sys
import logging
import gradio as gr
from urllib.parse import urljoin
from config import AppSettings

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import openai

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.info("Starting app")

settings = AppSettings.load("./settings.yml")
if len(sys.argv) > 1:
    settings.hf_model_name = sys.argv[1]
logger.info("App settings: %s", settings)

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
    model=settings.hf_model_name,
    openai_api_key="required-but-not-used",
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
    model_kwargs={
        "top_p": settings.llm_top_p,
        "frequency_penalty": settings.llm_frequency_penalty,
        "presence_penalty": settings.llm_presence_penalty,
        # Additional parameters supported by vLLM but not OpenAI API
        # https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html#extra-parameters
        "extra_body": {
            "top_k": settings.llm_top_k,
        }
    },
    streaming=True,
)


def inference(latest_message, history):
    # Allow mutating global variable
    global BACKEND_INITIALISED

    try:
        if INCLUDE_SYSTEM_PROMPT:
            context = [SystemMessage(content=settings.hf_model_instruction)]
        else:
            context = []
        for i, (human, ai) in enumerate(history):
            if not INCLUDE_SYSTEM_PROMPT and i == 0:
                # Mimic system prompt by prepending it to first human message
                human = f"{settings.hf_model_instruction}\n\n{human}"
            context.append(HumanMessage(content=human))
            context.append(AIMessage(content=(ai or "")))
        context.append(HumanMessage(content=latest_message))
        logger.debug("Chat context: %s", context)

        response = ""
        for chunk in llm.stream(context):
            # If this is our first successful response from the backend
            # then update the status variable to allow future error messages
            # to be more informative
            if not BACKEND_INITIALISED and len(response) > 0:
                BACKEND_INITIALISED = True

            # NOTE(sd109): For some reason the '>' character breaks the UI
            # so we need to escape it here.
            # response += chunk.content.replace('>', '\>')
            # UPDATE(sd109): Above bug seems to have been fixed as of gradio 4.15.0
            # but keeping this note here incase we enounter it again
            response += chunk.content
            yield response

    # Handle any API errors here. See OpenAI Python client for possible error responses
    # https://github.com/openai/openai-python/tree/e8e5a0dc7ccf2db19d7f81991ee0987f9c3ae375?tab=readme-ov-file#handling-errors

    except openai.BadRequestError as err:
        logger.error("Received BadRequestError from backend API: %s", err)
        message = err.response.json()["message"]
        if INCLUDE_SYSTEM_PROMPT:
            raise PossibleSystemPromptException()
        else:
            # In this case we've already tried without system prompt and still hit a bad request error so something else must be wrong
            ui_message = f"API Error received. This usually means the chosen LLM uses an incompatible prompt format. Error message was: {message}"
            raise gr.Error(ui_message)

    except openai.APIConnectionError as err:
        if not BACKEND_INITIALISED:
            logger.info("Backend API not yet ready")
            gr.Info(
                "Backend not ready - model may still be initialising - please try again later."
            )
        else:
            logger.error("Failed to connect to backend API: %s", err)
            gr.Warning("Failed to connect to backend API.")

    except openai.InternalServerError as err:
        gr.Warning(
            "Internal server error encountered in backend API - see API logs for details."
        )

    # Catch-all for unexpected exceptions
    except Exception as err:
        logger.error("Unexpected error during inference: %s", err)
        raise gr.Error("Unexpected error encountered - see logs for details.")


# UI theming
theme = gr.themes.Default(**settings.theme_params)
if settings.theme_background_colour:
    theme.body_background_fill = settings.theme_background_colour


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
        logger.warning("Disabling system prompt and retrying previous request")
        INCLUDE_SYSTEM_PROMPT = False
        for chunk in inference(*args):
            yield chunk


# Build main chat interface
with gr.ChatInterface(
    inference_wrapper,
    chatbot=gr.Chatbot(
        # Height of conversation window in CSS units (string) or pixels (int)
        height="68vh",
        show_copy_button=True,
    ),
    textbox=gr.Textbox(
        placeholder="Ask me anything...",
        container=False,
        # Ratio of text box to submit button width
        scale=7,
    ),
    title=settings.page_title,
    description=settings.page_description,
    retry_btn="Retry",
    undo_btn="Undo",
    clear_btn="Clear",
    analytics_enabled=False,
    theme=theme,
    css=settings.css_overrides,
    js=settings.custom_javascript,
) as app:
    logger.debug("Gradio chat interface config: %s", app.config)
    # For running locally in tilt dev setup
    if len(sys.argv) > 2 and sys.argv[2] == "localhost":
        app.launch()
    # For running on cluster
    else:
        app.queue(
            # Allow 10 concurrent requests to backend
            # vLLM backend should be clever enough to
            # batch these requests appropriately.
            default_concurrency_limit=10,
        ).launch(server_name="0.0.0.0")
