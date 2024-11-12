#####
# Based on demo_gr.py in repo root
#####

import time

import torch
import numpy as np
from einops import rearrange
from PIL import Image, ExifTags
from transformers import pipeline

from flux.cli import SamplingOptions
from flux.sampling import denoise, get_noise, get_schedule, prepare, unpack
from flux.util import embed_watermark, load_ae, load_clip, load_flow_model, load_t5

NSFW_THRESHOLD = 0.85

def get_models(name: str, device: torch.device, offload: bool, is_schnell: bool):
    t5 = load_t5(device, max_length=256 if is_schnell else 512)
    clip = load_clip(device)
    model = load_flow_model(name, device="cpu" if offload else device)
    ae = load_ae(name, device="cpu" if offload else device)
    nsfw_classifier = pipeline("image-classification", model="Falconsai/nsfw_image_detection", device=device)
    return model, ae, t5, clip, nsfw_classifier

class FluxGenerator:
    def __init__(self, model_name: str, device: str, offload: bool):
        self.device = torch.device(device)
        self.offload = offload
        self.model_name = model_name
        self.is_schnell = model_name == "flux-schnell"
        self.model, self.ae, self.t5, self.clip, self.nsfw_classifier = get_models(
            model_name,
            device=self.device,
            offload=self.offload,
            is_schnell=self.is_schnell,
        )

    @torch.inference_mode()
    def generate_image(
        self,
        width,
        height,
        num_steps,
        guidance,
        seed,
        prompt,
        init_image=None,
        image2image_strength=0.0,
        add_sampling_metadata=True,
    ):
        seed = int(seed)
        if seed == -1:
            seed = None

        opts = SamplingOptions(
            prompt=prompt,
            width=width,
            height=height,
            num_steps=num_steps,
            guidance=guidance,
            seed=seed,
        )

        if opts.seed is None:
            opts.seed = torch.Generator(device="cpu").seed()
        t0 = time.perf_counter()

        if init_image is not None:
            if isinstance(init_image, np.ndarray):
                init_image = torch.from_numpy(init_image).permute(2, 0, 1).float() / 255.0
                init_image = init_image.unsqueeze(0)
            init_image = init_image.to(self.device)
            init_image = torch.nn.functional.interpolate(init_image, (opts.height, opts.width))
            if self.offload:
                self.ae.encoder.to(self.device)
            init_image = self.ae.encode(init_image.to())
            if self.offload:
                self.ae = self.ae.cpu()
                torch.cuda.empty_cache()

        # prepare input
        x = get_noise(
            1,
            opts.height,
            opts.width,
            device=self.device,
            dtype=torch.bfloat16,
            seed=opts.seed,
        )
        timesteps = get_schedule(
            opts.num_steps,
            x.shape[-1] * x.shape[-2] // 4,
            shift=(not self.is_schnell),
        )
        if init_image is not None:
            t_idx = int((1 - image2image_strength) * num_steps)
            t = timesteps[t_idx]
            timesteps = timesteps[t_idx:]
            x = t * x + (1.0 - t) * init_image.to(x.dtype)

        if self.offload:
            self.t5, self.clip = self.t5.to(self.device), self.clip.to(self.device)
        inp = prepare(t5=self.t5, clip=self.clip, img=x, prompt=opts.prompt)

        # offload TEs to CPU, load model to gpu
        if self.offload:
            self.t5, self.clip = self.t5.cpu(), self.clip.cpu()
            torch.cuda.empty_cache()
            self.model = self.model.to(self.device)

        # denoise initial noise
        x = denoise(self.model, **inp, timesteps=timesteps, guidance=opts.guidance)

        # offload model, load autoencoder to gpu
        if self.offload:
            self.model.cpu()
            torch.cuda.empty_cache()
            self.ae.decoder.to(x.device)

        # decode latents to pixel space
        x = unpack(x.float(), opts.height, opts.width)
        with torch.autocast(device_type=self.device.type, dtype=torch.bfloat16):
            x = self.ae.decode(x)

        if self.offload:
            self.ae.decoder.cpu()
            torch.cuda.empty_cache()

        t1 = time.perf_counter()

        print(f"Done in {t1 - t0:.1f}s.")
        # bring into PIL format
        x = x.clamp(-1, 1)
        x = embed_watermark(x.float())
        x = rearrange(x[0], "c h w -> h w c")

        img = Image.fromarray((127.5 * (x + 1.0)).cpu().byte().numpy())
        nsfw_score = [x["score"] for x in self.nsfw_classifier(img) if x["label"] == "nsfw"][0] # type: ignore

        if nsfw_score < NSFW_THRESHOLD:
            exif_data = Image.Exif()
            if init_image is None:
                exif_data[ExifTags.Base.Software] = "AI generated;txt2img;flux"
            else:
                exif_data[ExifTags.Base.Software] = "AI generated;img2img;flux"
            exif_data[ExifTags.Base.Make] = "Black Forest Labs"
            exif_data[ExifTags.Base.Model] = self.model_name
            if add_sampling_metadata:
                exif_data[ExifTags.Base.ImageDescription] = prompt

            return img, str(opts.seed), None
        else:
            return None, str(opts.seed), "Your generated image may contain NSFW content."
