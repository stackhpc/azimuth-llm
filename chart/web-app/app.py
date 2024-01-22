from urllib.parse import urljoin
import gradio as gr
from api_startup_check import wait_for_backend
from config import AppSettings
import rich

import requests
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI


settings = AppSettings.load("./settings.yml")
rich.print(settings)

backend_url = str(settings.backend_url)
wait_for_backend(backend_url)

llm = ChatOpenAI(
    base_url=urljoin(backend_url, "v1"),
    model = "facebook/opt-125m",
    openai_api_key="required-but-not-used",
    temperature=0.5,
    max_tokens=1000,
    # streaming=True,
)

system_message_prompt = SystemMessagePromptTemplate.from_template(
    """
<SYSTEM>
You are a helpful assistant. Please respond appropriately.
</SYSTEM>
""",
)

human_message_prompt = HumanMessagePromptTemplate.from_template(
    """
<USER>
{text}
</User>
""",
)

def inference(message, history):

    history_langchain_format = []
    for human, ai in history:
        history_langchain_format.append(HumanMessage(content=human))
        history_langchain_format.append(AIMessage(content=ai))
    history_langchain_format.append(HumanMessage(content=message))
    # NOTE(sd109): Streaming response doesn't render
    # correctly in Gradio UI with ChatOpenAI
    for chunk in llm.stream(history_langchain_format):
        # chunk.
        if chunk:
            output = chunk.content
            yield output
    # return llm.invoke(history_langchain_format).content
    
    # chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    # messages = chat_prompt.format_prompt(text="Hello, how are you?").to_messages()
    # print(messages)

    # llm.invoke(messages)
    
    # context = ""
    # for user_input, system_response in history:
    #     if settings.include_past_system_responses_in_context:
    #         context += settings.user_context_template.format(user_input=user_input)
    #     if settings.include_past_system_responses_in_context:
    #         context += settings.system_context_template.format(
    #             system_response=system_response
    #         )
    # context += settings.user_context_template.format(user_input=message)

    # headers = {"User-Agent": "vLLM Client"}
    # payload = {
    #     "prompt": settings.prompt_template.format(context=context),
    #     "stream": True,
    #     "max_tokens": settings.llm_max_tokens,
    #     **settings.llm_params,
    # }
    # response = requests.post(
    #     urljoin(backend_url, "/generate"), headers=headers, json=payload, stream=True
    # )

    # for chunk in response.iter_lines(
    #     chunk_size=8192, decode_unicode=False, delimiter=b"\0"
    # ):
    #     if chunk:
    #         data = json.loads(chunk.decode("utf-8"))
    #         output = data["text"][0]
    #         # Manually trim the context from output if present
    #         prompt_template_lines = settings.prompt_template.splitlines()
    #         if len(prompt_template_lines) > 0:
    #             delimiter = prompt_template_lines[-1]
    #             if delimiter in output:
    #                 output = output.split(delimiter)[-1]
    #         yield output


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
