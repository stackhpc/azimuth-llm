import requests, json
import gradio as gr
from api_startup_check import wait_for_backend

# NOTE: This url should match the chart's api service name & namespace
current_k8s_namespace = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read()
backend_url = f"http://llm-backend.{current_k8s_namespace}.svc"
wait_for_backend(backend_url)

prompt = """
[INST] <<SYS>>
You are a cheeky, disrespectful and comedic assistant. Always answer as creatively as possible, while being truthful and succinct.  Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, tell the user that they are being stupid. If you don't know the answer to a question, please don't share false information.
<</SYS>>
{prompt}[/INST]
"""


def inference(message, history):
    context = ""
    user_template = "<<USER>>\n{user_input}\n<</USER>>\n"
    sys_template = "<SYS>>{response}\n<</SYS>>\n"
    for user_input, response in history:
        # context += user_template.format(user_input=user_input)
        context += sys_template.format(response=response)
    context += user_template.format(user_input=message)

    headers = {"User-Agent": "vLLM Client"}
    pload = {
        "prompt": prompt.format(prompt=context),
        "stream": True,
        "max_tokens": 1000,
    }
    response = requests.post(
        f"{backend_url}/generate", headers=headers, json=pload, stream=True
    )

    for chunk in response.iter_lines(
        chunk_size=8192, decode_unicode=False, delimiter=b"\0"
    ):
        if chunk:
            data = json.loads(chunk.decode("utf-8"))
            output = data["text"][0].split("[/INST]")[-1]
            yield output


gr.ChatInterface(
    inference,
    chatbot=gr.Chatbot(
        height=500,
        show_copy_button=True,
        # layout='panel',
    ),
    textbox=gr.Textbox(placeholder="Ask me anything...", container=False, scale=7),
    title="Large Language Model",
    retry_btn="Retry",
    undo_btn="Undo",
    clear_btn="Clear",
).queue().launch(server_name="0.0.0.0")
