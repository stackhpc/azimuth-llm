FROM ghcr.io/astral-sh/uv:python3.11-bookworm

# https://stackoverflow.com/questions/55313610/importerror-libgl-so-1-cannot-open-shared-object-file-no-such-file-or-directo
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y


ARG DIR=flux-image-gen

COPY $DIR/requirements.txt requirements.txt
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY purge-google-fonts.sh .
RUN bash purge-google-fonts.sh

WORKDIR /app

COPY $DIR/*.py .

COPY $DIR/gradio_config.yaml .

COPY $DIR/test-image.jpg .

ENTRYPOINT ["fastapi", "run", "api_server.py"]
