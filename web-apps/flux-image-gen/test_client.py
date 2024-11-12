import os
from gradio_client import Client

address = os.environ.get("GRADIO_HOST", "http://localhost:7860/")
model = os.environ.get("FLUX_MODEL", "flux-schnell")
client = Client(address)
web_page, seed, file_name, err = client.predict(
		model_name=model,
		# width=1360,
		width=3888,
		# height=768,
		height=2544,
		num_steps=4,
		guidance=3.5,
		seed="-1",
		prompt="Yoda riding a skateboard",
		add_sampling_metadata=True,
		api_name="/generate_image"
)
print('Result saved to:', file_name)
