FROM ghcr.io/astral-sh/uv:python3.11-trixie-slim

RUN apt-get update && apt-get install -y \
      libssl3t64=3.5.6-1~deb13u2 \
      openssl=3.5.6-1~deb13u2 \
      libsqlite3-0=3.46.1-7+deb13u1 \
      libgnutls30t64=3.8.9-3+deb13u4 \
    && rm -rf /var/lib/apt/lists/*

ARG DIR=chat

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
