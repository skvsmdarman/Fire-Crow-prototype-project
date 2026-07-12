FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libcairo2 \
       libgdk-pixbuf-2.0-0 \
       libffi-dev \
       shared-mime-info \
       git \
       libxml2-dev \
       libxslt1-dev \
       libxmlsec1-dev \
       libxmlsec1-openssl \
       xmlsec1 \
       pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/

EXPOSE 10000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-10000}/health/live || exit 1

CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
