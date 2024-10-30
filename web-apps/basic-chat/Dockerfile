FROM python:3.11-slim

ARG DIR=chat-interface

COPY $DIR/requirements.txt requirements.txt
COPY utils utils
RUN pip install --no-cache-dir -r requirements.txt

COPY purge-google-fonts.sh purge-google-fonts.sh
RUN bash purge-google-fonts.sh

WORKDIR /app

COPY $DIR/*.py .

COPY $DIR/defaults.yml .

ENTRYPOINT ["python3", "app.py"]
