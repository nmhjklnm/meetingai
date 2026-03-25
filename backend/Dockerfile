FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
# Stubs so uv can resolve workspace — dependencies cached until pyproject.toml/uv.lock change
RUN mkdir -p backend ml_services && touch backend/__init__.py ml_services/__init__.py
RUN uv sync --no-dev && uv run uvicorn --version
# Copy actual source (cheap layer)
COPY backend/ ./backend/
COPY ml_services/ ./ml_services/

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
