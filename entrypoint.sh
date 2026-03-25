#!/bin/sh
set -e

# 首次运行：把依赖安装到 volume（/app/.venv）
# 后续运行：volume 已有包，uv 做 hash 校验后秒级返回
uv sync --no-dev

exec "$@"
