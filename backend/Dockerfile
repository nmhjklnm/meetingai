FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# PyTorch CPU-only 索引（省 ~1.8GB，该机器无 GPU）
ENV UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/
COPY ml_services/ ./ml_services/
RUN uv sync --no-dev && uv run uvicorn --version

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
