#!/bin/sh
set -e

# 首次运行：生成 lockfile + 安装依赖到 volume（/app/.venv）
# 后续运行：volume 已有包，uv 做 hash 校验后秒级返回
export UV_LINK_MODE=copy
uv lock --check 2>/dev/null || uv lock
uv sync --no-dev

exec "$@"
