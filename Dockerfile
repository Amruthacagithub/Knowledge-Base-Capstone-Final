# Knowledge Base API — Google Cloud Run (and local docker build)
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.12.0 \
            --index-url https://download.pytorch.org/whl/cpu \
        && pip install --no-cache-dir -r requirements.txt

# Models download on first request (avoids Cloud Build OOM). Cold start is slower once.

COPY backend ./backend
COPY documents ./documents
COPY scripts ./scripts
COPY pytest.ini .
COPY alembic.ini .
COPY migrations ./migrations
RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app \
    && mkdir -p /app/indexdir \
    && chown -R app:app /app /home/app

ENV PORT=8080
ENV HF_HOME=/home/app/.cache/huggingface
EXPOSE 8080

USER app

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
