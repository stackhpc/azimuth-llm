FROM python:3.11-slim

ENV GRADIO_SERVER_PORT=7680

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY purge-google-fonts.sh purge-google-fonts.sh
RUN bash purge-google-fonts.sh
