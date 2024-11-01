import sys
from gradio_client import Client

gradio_host = sys.argv[1]
client = Client(gradio_host)
result = client.predict("Hi", api_name="/chat")
print(result)
