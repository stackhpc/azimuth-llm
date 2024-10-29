FROM python:3.11-slim

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY purge-google-fonts.sh purge-google-fonts.sh
RUN bash purge-google-fonts.sh

WORKDIR /app

COPY *.py .

COPY defaults.yml .
# COPY overrides.yml .

ENTRYPOINT ["python3", "app.py"]
