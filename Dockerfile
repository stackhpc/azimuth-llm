
FROM amd64/python:3.11-slim

ENV GRADIO_SERVER_PORT=7680

RUN pip install gradio==3.50.2 huggingface-hub==0.18.0
