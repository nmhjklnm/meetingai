"""
WebSocket — 实时进度推送
========================
WS /ws/meetings/{id}/progress

客户端连接后，服务端每秒轮询 Redis，将进度 JSON 推送给前端。
连接断开或任务完成（status=done/failed）时关闭。
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.redis_client import get_progress

router = APIRouter()

POLL_INTERVAL = 1.0   # 秒


@router.websocket("/ws/meetings/{meeting_id}/progress")
async def ws_progress(websocket: WebSocket, meeting_id: str):
    await websocket.accept()
    try:
        while True:
            progress = get_progress(meeting_id)
            if progress:
                await websocket.send_text(json.dumps(progress, ensure_ascii=False))
                if progress.get("status") in ("done", "failed"):
                    break
            else:
                await websocket.send_text(json.dumps({
                    "status": "pending",
                    "message": "等待任务启动...",
                }))
            await asyncio.sleep(POLL_INTERVAL)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
