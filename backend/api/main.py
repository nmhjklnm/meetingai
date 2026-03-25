"""
FastAPI 主应用
==============
REST API + WebSocket 实时进度推送
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（首次部署无需手动迁移）
    from backend.core.database import Base, get_engine
    import backend.models  # noqa: F401 — 触发模型注册
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # 确保音频目录存在
    from pathlib import Path
    from backend.core.config import get_settings
    Path(get_settings().audio_dir).mkdir(parents=True, exist_ok=True)

    yield


app = FastAPI(
    title="Meeting Transcriber API",
    description="会议语音转写 + 说话人分离 + 智能摘要",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 路由注册 ──────────────────────────────────────────────────────────────────
from backend.api.routes.meetings import router as meetings_router  # noqa: E402
from backend.api.routes.websocket import router as ws_router       # noqa: E402
from backend.api.routes.system import router as system_router       # noqa: E402

app.include_router(meetings_router, prefix="/api/meetings", tags=["meetings"])
app.include_router(system_router, prefix="/api", tags=["system"])
app.include_router(ws_router, tags=["websocket"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
