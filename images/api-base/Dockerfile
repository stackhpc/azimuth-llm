FROM nvidia/cuda:12.2.2-runtime-ubi8
RUN dnf install -y python3.11-pip && dnf clean all
RUN python3.11 -m pip install --no-cache-dir vllm && python3.11 -m pip cache purge