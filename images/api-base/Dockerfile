FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04
RUN apt-get update && \
    apt-get install -y python3-pip python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir vllm