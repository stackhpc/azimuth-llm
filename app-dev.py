import huggingface_hub
from huggingface_hub import InferenceClient
import gradio as gr

client = InferenceClient(model="http://text-generation-inference.default.svc")

def inference(message, history):
    
    if message == "":
        yield ""

    # print(history)
    partial_message = "" 
    # for token in client.text_generation(message, max_new_tokens=500, stream=True):
    # input = message
    # input = "".join(history[0]) + message if len(history) > 0 else message

    # Instruction header    
    # input = ">>> You are a helpful chat bot who gives succinct but informative responses. Never get angry. Do not output any lines starting with 'USER' or 'RESPONSE'.<<<\n"
    input = ">>> You are a helpful chat bot who gives succinct but informative responses. Never get angry. <<<\n"

    # History
    # for (user, response) in history:
    #     # input += f"USER: {user}\nRESPONSE: {response}\n\n"
    #     input += f"{user}\n{response}\n\n"
    if len(history) > 0:
        input += f"{history[-1][0]}\n{history[-1][1]}"
    
    # User input 
    input += f"{message}\n"
    
    # Logging
    print("-----\nInput:", input, "\n-----")
    
    try:
        for token in client.text_generation(input, max_new_tokens=500, stream=True):
            partial_message += token
            # Strip text marker from generated output
            # partial_message = partial_message.replace('<|endoftext|>', '')
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