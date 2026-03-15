"""
FastAPI 主应用
==============
REST API + WebSocket 实时进度推送
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Meeting Transcriber API",
    description="会议语音转写 + 说话人分离 + 智能摘要",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 路由注册（TODO: 实现各路由） ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# POST   /api/meetings              上传音频，创建转写任务
# GET    /api/meetings              获取历史会议列表
# GET    /api/meetings/{id}         获取会议详情 + 转录结果
# GET    /api/meetings/{id}/summary 获取 AI 摘要
# PATCH  /api/meetings/{id}/speakers 更新说话人姓名映射
# DELETE /api/meetings/{id}         删除会议
# WS     /ws/meetings/{id}/progress 实时转写进度推送

# TODO: from .routes import meetings, speakers, export
# app.include_router(meetings.router, prefix="/api/meetings")
