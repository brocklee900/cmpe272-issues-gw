FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY openapi.yaml .

# Data dir for the SQLite webhook-event store.
RUN mkdir -p /app/data

EXPOSE 8000

# PORT is read by app/config.py; uvicorn's own bind port below should match
# whatever you pass via --env-file / -e PORT=... at `docker run` time.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
