import requests
import warnings
import rich
import gradio as gr
from urllib.parse import urljoin
from api_startup_check import wait_for_backend
from config import AppSettings

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI


settings = AppSettings.load("./settings.yml")
print("App settings:")
rich.print(settings)

backend_url = str(settings.backend_url)
backend_health_endpoint = urljoin(backend_url, "/health")
wait_for_backend(backend_health_endpoint)

# TODO: Think about whether we want to run the vLLM model here
# in an AIO setup instead of separate frontend/backend components
# from langchain_community.llms import VLLM
# llm = VLLM()

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
        response = requests.get(backend_health_endpoint, timeout=1)
        if response.status_code != 200:
            raise gr.Error("Backend reachable but unhealthy. Please try again later")
    except Exception as err:
        warnings.warn(f"Error while checking backend health: {err}")
        raise gr.Error("Backend unreachable. Please try again later")

    try:
        context = [SystemMessage(content=settings.model_instruction)]
        for human, ai in history:
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
