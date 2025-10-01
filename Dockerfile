# syntax=docker/dockerfile:1
FROM python:3.13-slim AS tests

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip uv

COPY pyproject.toml README.md ./
COPY app ./app
COPY tests ./tests

RUN uv pip install --system --no-cache ".[dev]"
RUN pytest

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/app appuser

RUN mkdir -p /app \
    && chown appuser:appuser /app

WORKDIR /app

COPY --chown=appuser:appuser pyproject.toml README.md ./
COPY --chown=appuser:appuser app ./app

RUN pip install --no-cache-dir --upgrade pip uv \
    && uv pip install --system --no-cache .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
