import io
import os
import sys
import torch

from fastapi import FastAPI
from fastapi.responses import Response, JSONResponse
from PIL import Image
from pydantic import BaseModel

from image_gen import FluxGenerator

# Detect if app is run using `fastapi dev ...`
DEV_MODE = sys.argv[1] == "dev"

app = FastAPI()

device = "cuda" if torch.cuda.is_available() else "cpu"
model = os.environ.get("FLUX_MODEL_NAME", "flux-schnell")
if not DEV_MODE:
    print("Loading model", model)
    generator = FluxGenerator(model, device, offload=False)


class ImageGenInput(BaseModel):
    width: int
    height: int
    num_steps: int
    guidance: float
    seed: int
    prompt: str
    add_sampling_metadata: bool

@app.get("/")
def health_check():
    return "Server is running"

@app.get("/model")
async def get_model():
    return {"model": model}


@app.post("/generate")
async def generate_image(input: ImageGenInput):
    if DEV_MODE:
        # For quicker testing or when GPU hardware not available
        fn = "test-image.jpg"
        seed = "dev"
        image = Image.open(fn)
        # Uncomment to test error handling
        # return JSONResponse({"error": {"message": "Dev mode error test", "seed": "not-so-random"}}, status_code=400)
    else:
        # Main image generation functionality
        image, seed, msg = generator.generate_image(
            input.width,
            input.height,
            input.num_steps,
            input.guidance,
            input.seed,
            input.prompt,
            add_sampling_metadata=input.add_sampling_metadata,
        )
        if not image:
            return JSONResponse({"error": {"message": msg, "seed": seed}}, status_code=400)
    # Convert image to bytes response
    buffer = io.BytesIO()
    image.save(buffer, format="jpeg")
    bytes = buffer.getvalue()
    return Response(bytes, media_type="image/jpeg", headers={"x-flux-seed": seed})
