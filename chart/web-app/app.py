import requests
import re
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
logger.info("App settings: %s", settings)

backend_url = str(settings.backend_url)
backend_health_endpoint = urljoin(backend_url, "/health")
BACKEND_INITIALISED = False

# # NOTE(sd109): The Mistral family of models explicitly require a chat
# # history of the form user -> ai -> user -> ... and so don't like having
# # a SystemPrompt at the beginning. Since these models seem to be the
# # best around right now, it makes sense to treat them as special and make
# # sure the web app works correctly with them. To do so, we detect when a
# # mistral model is specified using this regex and then handle it explicitly
# # when contructing the `context` list in the `inference` function below.
# MISTRAL_REGEX = re.compile(r".*mi(s|x)tral.*", re.IGNORECASE)
# IS_MISTRAL_MODEL = MISTRAL_REGEX.match(settings.model_name) is not None
# if IS_MISTRAL_MODEL:
#     print(
#         "Detected Mistral model - will alter LangChain conversation format appropriately."
#     )

# Some models disallow 'system' role's their conversation history by raising errors in their chat prompt template, e.g. see
# https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/blob/cf47bb3e18fe41a5351bc36eef76e9c900847c89/tokenizer_config.json#L42
# Detecting this ahead of time is difficult so for now we use a global variable which stores whether the API has
# responded with a HTTP 400 error and retry request without system role replaced by
INCLUDE_SYSTEM_PROMPT = True

llm = ChatOpenAI(
    base_url=urljoin(backend_url, "v1"),
    model=settings.model_name,
    openai_api_key="required-but-not-used",
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
    model_kwargs={
        "top_p": settings.llm_top_p,
        "frequency_penalty": settings.llm_frequency_penalty,
        "presence_penalty": settings.llm_presence_penalty,
    },
    streaming=True,
)


def inference(latest_message, history):
    # Check backend health and warn the user on error
    # try:
    #     response = requests.get(backend_health_endpoint, timeout=5)
    #     response_code = response.status_code
    #     if response_code == 200:
    #         global backend_initialised
    #         if not backend_initialised:
    #             # Record the fact that backend was up at one point so we know that
    #             # any future errors are not related to slow model initialisation
    #             backend_initialised = True
    #     elif response_code >= 400 and response_code < 500:
    #         logging.warn(f"Received HTTP {response_code} response from backend. Full response: {response.text}")
    #     else:
    #         # If the server's running (i.e. we get a response) but it's not an HTTP 200
    #         # we just hope Kubernetes reconciles things for us eventually..
    #         raise gr.Error("Backend unhealthy - please try again later")
    # except Exception as err:
    #     warnings.warn(f"Error while checking backend health: {err}")
    #     if backend_initialised:
    #         # If backend was previously reachable then something unexpected has gone wrong
    #         raise gr.Error("Backend unreachable")
    #     else:
    #         # In this case backend is probably still busy downloading model weights
    #         raise gr.Error("Backend not ready yet - please try again later")

    # try:
    #     # To handle Mistral models we have to add the model instruction to
    #     # the first user message since Mistral requires user -> ai -> user
    #     # chat format and therefore doesn't allow system prompts.
    #     context = []
    #     if not IS_MISTRAL_MODEL:
    #         context.append(SystemMessage(content=settings.model_instruction))
    #     for i, (human, ai) in enumerate(history):
    #         if IS_MISTRAL_MODEL and i == 0:
    #             context.append(
    #                 HumanMessage(content=f"{settings.model_instruction}\n\n{human}")
    #             )
    #         else:
    #             context.append(HumanMessage(content=human))
    #         context.append(AIMessage(content=ai))
    #     context.append(HumanMessage(content=latest_message))

    #     response = ""
    #     for chunk in llm.stream(context):
    #         # print(chunk)
    #         # NOTE(sd109): For some reason the '>' character breaks the UI
    #         # so we need to escape it here.
    #         # response += chunk.content.replace('>', '\>')
    #         # UPDATE(sd109): Above bug seems to have been fixed as of gradio 4.15.0
    #         # but keeping this note here incase we enounter it again
    #         response += chunk.content
    #         yield response

    # # For all other errors notify user and log a more detailed warning
    # except Exception as err:
    #     warnings.warn(f"Exception encountered while generating response: {err}")
    #     raise gr.Error(
    #         "Unknown error encountered - see application logs for more information."
    #     )


    # Allow mutating global variables
    global BACKEND_INITIALISED, INCLUDE_SYSTEM_PROMPT

    try:
        # Attempt to handle models which disallow system prompts
        # Construct conversation history for model prompt
        if INCLUDE_SYSTEM_PROMPT:
            context = [SystemMessage(content=settings.model_instruction)]
        else:
            context = []
        for i, (human, ai) in enumerate(history):
            if not INCLUDE_SYSTEM_PROMPT and i == 0:
                # Mimic system prompt by prepending it to first human message
                human = f"{settings.model_instruction}\n\n{human}"
            context.append(HumanMessage(content=human))
            context.append(AIMessage(content=(ai or "")))
        context.append(HumanMessage(content=latest_message))

        response = ""
        for chunk in llm.stream(context):

            # If this is our first successful response from the backend
            # then update the status variable
            if not BACKEND_INITIALISED and len(response) > 0:
                BACKEND_INITIALISED = True

            # NOTE(sd109): For some reason the '>' character breaks the UI
            # so we need to escape it here.
            # response += chunk.content.replace('>', '\>')
            # UPDATE(sd109): Above bug seems to have been fixed as of gradio 4.15.0
            # but keeping this note here incase we enounter it again
            response += chunk.content
            yield response

    except openai.BadRequestError as err:
        logger.error("Received BadRequestError from backend API: %s", err)
        message = err.response.json()['message']
        if INCLUDE_SYSTEM_PROMPT:
            INCLUDE_SYSTEM_PROMPT = False
            # TODO: Somehow retry same inference step without system prompt
            pass
        ui_message = f"API Error received. This usually means the chosen LLM uses an incompatible prompt format. Error message was: {message}"
        raise gr.Error(ui_message)

    except openai.APIConnectionError as err:
        if not BACKEND_INITIALISED:
            logger.info("Backend API not yet ready")
            gr.Info("Backend not ready - model may still be initialising - please try again later")
        else:
            logger.error("Failed to connect to backend API: %s", err)
            gr.Warning("Failed to connect to backend API")

    except openai.InternalServerError as err:
        gr.Warning("Internal server error encountered in backend API - see API logs for details.")

    # Catch-all for unexpected exceptions
    except Exception as err:
        logger.error("Unexpected error during inference: %s", err)
        raise gr.Error("Unexpected error encountered - see logs for details.")


# UI colour theming
theme = gr.themes.Default(**settings.theme_params)
if settings.theme_background_colour:
    theme.body_background_fill = settings.theme_background_colour

css_overrides = ""
if settings.theme_title_colour:
    css_overrides += """
    h1 {{
        color: {0};
        padding-top: 0.5em;
    }}
    """.format(
        settings.theme_title_colour
    )


# Build main chat interface
with gr.ChatInterface(
    inference,
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
    retry_btn="Retry",
    undo_btn="Undo",
    clear_btn="Clear",
    analytics_enabled=False,
    theme=theme,
    css=css_overrides,
) as app:
    # app.launch(server_name="0.0.0.0") # Do we need this for k8s service?
    app.launch()
