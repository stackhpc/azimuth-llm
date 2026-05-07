FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update && \
    apt-get install -y --only-upgrade libssl3=3.0.19-1~deb12u2 openssl=3.0.19-1~deb12u2 && \
    rm -rf /var/lib/apt/lists/*

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
