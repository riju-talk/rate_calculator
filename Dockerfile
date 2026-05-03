FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /venv \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system appuser \
    && adduser --system --ingroup appuser appuser

COPY --from=builder /venv /venv
COPY --chown=appuser:appuser . /app

RUN chmod +x /app/scripts/entrypoint.sh /app/scripts/wait-for-it.sh \
    && mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app/staticfiles

USER appuser

EXPOSE 8000

CMD ["./scripts/entrypoint.sh"]
