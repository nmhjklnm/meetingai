#!/usr/bin/env bash
# ============================================================
# 本地开发一键启动脚本
# 启动顺序：
#   1. VAD 微服务        (port 8001)  ← 加载 FSMN-VAD
#   2. 说话人分离微服务   (port 8002)  ← 加载 CAM++
#   3. Celery Worker
#   4. 主 API            (port 8000)
#
# 前置依赖：
#   - Redis（brew install redis && brew services start redis）
#   - ffmpeg（brew install ffmpeg）
#   - uv（curl -LsSf https://astral.sh/uv/install.sh | sh）
#   - 已在 .env 中配置 OPENAI_API_KEY 和 OPENAI_BASE_URL
# ============================================================
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/data/logs"
mkdir -p "$LOG_DIR" "$ROOT/data/audio" "$ROOT/data/models_cache"

# ── 颜色输出 ────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── 检测依赖 ────────────────────────────────────────────────
command -v uv    >/dev/null || error "未找到 uv，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v ffmpeg >/dev/null || error "未找到 ffmpeg，请安装: brew install ffmpeg"
command -v redis-cli >/dev/null && redis-cli ping >/dev/null 2>&1 || warn "Redis 未运行，尝试启动..."
redis-cli ping >/dev/null 2>&1 || { brew services start redis 2>/dev/null || redis-server --daemonize yes; sleep 1; }
redis-cli ping >/dev/null 2>&1 || error "Redis 启动失败，请手动启动: redis-server"
info "Redis 已就绪"

# ── 安装/同步 Python 依赖 ────────────────────────────────────
info "同步 Python 依赖..."
uv sync --no-dev 2>&1 | tail -3

# ── 设置 ModelScope 缓存目录 ─────────────────────────────────
export MODELSCOPE_CACHE="$ROOT/data/models_cache"

# ── 终止函数（Ctrl+C 时清理子进程） ─────────────────────────
PIDS=()
cleanup() {
    echo ""
    warn "正在关闭所有服务..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    info "所有服务已关闭"
    exit 0
}
trap cleanup INT TERM

# ── 1. 启动 VAD 微服务 ───────────────────────────────────────
info "启动 VAD 服务 (port 8001)..."
uv run uvicorn ml_services.vad_service:app \
    --host 0.0.0.0 --port 8001 --log-level info \
    > "$LOG_DIR/vad.log" 2>&1 &
VAD_PID=$!
PIDS[${#PIDS[@]}]=$VAD_PID

# ── 2. 启动说话人分离微服务 ──────────────────────────────────
info "启动说话人分离服务 (port 8002)..."
uv run uvicorn ml_services.diarization_service:app \
    --host 0.0.0.0 --port 8002 --log-level info \
    > "$LOG_DIR/diarization.log" 2>&1 &
DIAR_PID=$!
PIDS[${#PIDS[@]}]=$DIAR_PID

# ── 等待 ML 服务加载完成 ─────────────────────────────────────
echo ""
warn "等待 ML 模型加载（首次运行约需 1-3 分钟下载模型）..."
warn "  VAD 日志:            tail -f $LOG_DIR/vad.log"
warn "  说话人分离日志:      tail -f $LOG_DIR/diarization.log"

READY_VAD=0; READY_DIAR=0
for i in $(seq 1 120); do
    sleep 2
    if [ $READY_VAD -eq 0 ] && curl -sf http://localhost:8001/health >/dev/null 2>&1; then
        info "VAD 服务就绪 ✓"
        READY_VAD=1
    fi
    if [ $READY_DIAR -eq 0 ] && curl -sf http://localhost:8002/health >/dev/null 2>&1; then
        info "说话人分离服务就绪 ✓"
        READY_DIAR=1
    fi
    [ $READY_VAD -eq 1 ] && [ $READY_DIAR -eq 1 ] && break
    # 检查进程是否崩溃
    kill -0 $VAD_PID 2>/dev/null || { error "VAD 服务崩溃，查看日志: $LOG_DIR/vad.log"; }
    kill -0 $DIAR_PID 2>/dev/null || { error "说话人分离服务崩溃，查看日志: $LOG_DIR/diarization.log"; }
done

if [ $READY_VAD -eq 0 ] || [ $READY_DIAR -eq 0 ]; then
    warn "ML 服务加载超时（240s），请检查日志后重试"
fi

# ── 3. 启动 Celery Worker ────────────────────────────────────
info "启动 Celery Worker..."
uv run celery -A backend.worker.tasks worker \
    --loglevel=info --concurrency=2 \
    > "$LOG_DIR/worker.log" 2>&1 &
PIDS[${#PIDS[@]}]=$!
info "  Worker 日志: tail -f $LOG_DIR/worker.log"

sleep 2

# ── 4. 启动主 API（前台运行，方便看日志） ────────────────────
info "启动主 API (port 8000)..."
echo ""
echo "=================================================="
echo "  服务已全部启动"
echo "  API:             http://localhost:8000"
echo "  前端（单独启动）: cd frontend && npm run dev"
echo "  按 Ctrl+C 关闭所有服务"
echo "=================================================="
echo ""

uv run uvicorn backend.api.main:app \
    --host 0.0.0.0 --port 8000 \
    --reload --log-level info
