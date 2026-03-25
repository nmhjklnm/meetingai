FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
# Stub backend package so uv can resolve workspace without real backend code
RUN mkdir -p backend && touch backend/__init__.py
RUN uv sync --no-dev
# Only copy actual ml_services source (cheap layer, no dependency reinstall)
COPY ml_services/ ./ml_services/
