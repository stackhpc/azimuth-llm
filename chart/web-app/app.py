import requests
import warnings
import re
import rich
import gradio as gr
from urllib.parse import urljoin
from config import AppSettings

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI


settings = AppSettings.load("./settings.yml")
print("App settings:")
rich.print(settings)

backend_url = str(settings.backend_url)
backend_health_endpoint = urljoin(backend_url, "/health")
backend_initialised = False

# NOTE(sd109): The Mistral family of models explicitly require a chat
# history of the form user -> ai -> user -> ... and so don't like having
# a SystemPrompt at the beginning. Since these models seem to be the
# best around right now, it makes sense to treat them as special and make
# sure the web app works correctly with them. To do so, we detect when a
# mistral model is specified using this regex and then handle it explicitly
# when contructing the `context` list in the `inference` function below.
MISTRAL_REGEX = re.compile(r".*mi(s|x)tral.*", re.IGNORECASE)
IS_MISTRAL_MODEL = (MISTRAL_REGEX.match(settings.model_name) is not None)
if IS_MISTRAL_MODEL:
    print("Detected Mistral model - will alter LangChain conversation format appropriately.")

llm = ChatOpenAI(
    base_url=urljoin(backend_url, "v1"),
    model = settings.model_name,
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
    try:
        response = requests.get(backend_health_endpoint, timeout=5)
        if response.status_code == 200:
            global backend_initialised
            if not backend_initialised:
                # Record the fact that backend was up at one point so we know that
                # any future errors are not related to slow model initialisation
                backend_initialised = True
        else:
            # If the server's running (i.e. we get a response) but it's not an HTTP 200
            # we just hope Kubernetes reconciles things for us eventually..
            raise gr.Error("Backend unhealthy - please try again later")
    except Exception as err:
        warnings.warn(f"Error while checking backend health: {err}")
        if backend_initialised:
            # If backend was previously reachable then something unexpected has gone wrong
            raise gr.Error("Backend unreachable")
        else:
            # In this case backend is probably still busy downloading model weights
            raise gr.Error("Backend not ready yet - please try again later")


    try:
        # To handle Mistral models we have to add the model instruction to
        # the first user message since Mistral requires user -> ai -> user
        # chat format and therefore doesn't allow system prompts.
        context = []
        if not IS_MISTRAL_MODEL:
            context.append(SystemMessage(content=settings.model_instruction))
        for i, (human, ai) in enumerate(history):
            if IS_MISTRAL_MODEL and i == 0:
                context.append(HumanMessage(content=f"{settings.model_instruction}\n\n{human}"))
            else:
                context.append(HumanMessage(content=human))
            context.append(AIMessage(content=ai))
        context.append(HumanMessage(content=latest_message))

        response = ""
        for chunk in llm.stream(context):
            # print(chunk)
            # NOTE(sd109): For some reason the '>' character breaks the UI
            # so we need to escape it here.
            # response += chunk.content.replace('>', '\>')
            # UPDATE(sd109): Above bug seems to have been fixed as of gradio 4.15.0
            # but keeping this note here incase we enounter it again
            response += chunk.content
            yield response

    # For all other errors notify user and log a more detailed warning
    except Exception as err:
        warnings.warn(f"Exception encountered while generating response: {err}")
        raise gr.Error("Unknown error encountered - see application logs for more information.")


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
gr.ChatInterface(
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
).queue().launch(server_name="0.0.0.0")
