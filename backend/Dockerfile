FROM python:3.12-slim

WORKDIR /app

# 国内 Debian 镜像 + 安装 ffmpeg
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 国内 PyPI 镜像
ENV UV_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/
COPY ml_services/ ./ml_services/
RUN uv sync --no-dev --frozen && uv run uvicorn --version

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
