import requests, json
from urllib.parse import urljoin
import gradio as gr
from api_startup_check import wait_for_backend
from config import AppSettings

settings = AppSettings.load("./settings.yml")

backend_url = str(settings.backend_url)
wait_for_backend(backend_url)


def inference(message, history):
    context = ""
    for user_input, system_response in history:
        if settings.include_past_system_responses_in_context:
            context += settings.user_context_template.format(user_input=user_input)
        if settings.include_past_system_responses_in_context:
            context += settings.system_context_template.format(
                system_response=system_response
            )
    context += settings.user_context_template.format(user_input=message)

    headers = {"User-Agent": "vLLM Client"}
    payload = {
        "prompt": settings.prompt_template.format(context=context),
        "stream": True,
        "max_tokens": settings.llm_max_tokens,
        **settings.llm_params,
    }
    response = requests.post(
        urljoin(backend_url, "/generate"), headers=headers, json=payload, stream=True
    )

    for chunk in response.iter_lines(
        chunk_size=8192, decode_unicode=False, delimiter=b"\0"
    ):
        if chunk:
            data = json.loads(chunk.decode("utf-8"))
            output = data["text"][0]
            # Manually trim the context from output
            delimiter = settings.prompt_template.splitlines()[-1]
            if delimiter in output:
                output = output.split(delimiter)[-1]
            yield output


gr.ChatInterface(
    inference,
    chatbot=gr.Chatbot(
        height=500,
        show_copy_button=True,
        # layout='panel',
    ),
    textbox=gr.Textbox(placeholder="Ask me anything...", container=False, scale=7),
    title=settings.page_title,
    retry_btn="Retry",
    undo_btn="Undo",
    clear_btn="Clear",
).queue().launch(server_name="0.0.0.0")
