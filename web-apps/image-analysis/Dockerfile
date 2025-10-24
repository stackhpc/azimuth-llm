FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ARG DIR=image-analysis

COPY $DIR/requirements.txt requirements.txt
RUN sed -i s$../utils$./utils$ requirements.txt
COPY utils utils
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY purge-google-fonts.sh purge-google-fonts.sh
RUN bash purge-google-fonts.sh

WORKDIR /app

COPY $DIR/*.py .

COPY $DIR/defaults.yml .

ENTRYPOINT ["python3", "app.py"]
