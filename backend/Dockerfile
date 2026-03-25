FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 先拷贝依赖文件，利用 Docker 层缓存（代码变了不重装依赖）
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# 再拷贝代码
COPY backend/ ./backend/
COPY ml_services/ ./ml_services/

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
