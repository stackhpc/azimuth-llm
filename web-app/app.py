import huggingface_hub
from huggingface_hub import InferenceClient
import gradio as gr
from startup import wait_for_backend

backend_url = "http://text-generation-inference.default.svc"
wait_for_backend(backend_url)


client = InferenceClient(model=backend_url)

def inference(message, history):
    
    if message == "":
        yield ""

    partial_message = ""
    try:
        for token in client.text_generation(message, max_new_tokens=500, stream=True):
            partial_message += token
            # Strip text marker from generated output
            partial_message = partial_message.replace('<|endoftext|>', '')
            yield partial_message
    except huggingface_hub.inference._text_generation.ValidationError as e:
        # yield "Context length exceeded. Please clear the chat window."
        raise gr.Error("Context length exceeded. Please clear the chat window.")

gr.ChatInterface(
    inference,
    chatbot=gr.Chatbot(
        height=500,
        show_copy_button=True,
        # layout='panel',
    ),
    textbox=gr.Textbox(placeholder="Ask me anything...", container=False, scale=7),
    # description="This is the demo for Gradio UI consuming TGI endpoint.",
    title="Azimuth LLM",
    # examples=["What is OpenStack?", "Who are StackHPC?", "Give me the k8s pod yaml for an ubuntu container."],
    retry_btn="Retry",
    undo_btn="Undo",
    clear_btn="Clear",
).queue().launch(server_name="0.0.0.0")