"""
系统工具接口
============
POST /api/check-model       检测模型是否可用
GET  /api/progress/{id}     获取任务进度（Redis）
"""
from __future__ import annotations

from typing import Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.config import get_settings
from backend.core.redis_client import get_progress

router = APIRouter()


@router.get("/progress/{meeting_id}")
async def get_meeting_progress(meeting_id: str, suffix: str = ""):
    """获取会议任务进度（从 Redis 读取）。suffix 区分子任务（timeline / summary）。"""
    progress = get_progress(meeting_id, suffix=suffix)
    if progress:
        return progress
    return {"status": "idle"}


class CheckModelRequest(BaseModel):
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@router.post("/check-model")
async def check_model(body: CheckModelRequest):
    """
    检测指定模型是否可用。
    尝试调用 GET /models/{model} 端点，成功则可用。
    """
    settings = get_settings()
    base = (body.base_url or settings.openai_base_url).rstrip("/")
    key = body.api_key or settings.openai_api_key

    if not key:
        return {"available": False, "error": "未配置 API Key"}

    url = f"{base}/models/{body.model}"
    headers = {"Authorization": f"Bearer {key}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return {"available": True}
            # 有些代理不支持 /models 端点，尝试 chat completions 兜底
            if "transcribe" in body.model or "whisper" in body.model:
                # 转录模型无法通过 chat 测试，/models 404 就认为需要实测
                return {"available": True, "warning": "无法预检转录模型，将在实际使用时验证"}
            # 尝试最小 chat completion
            chat_url = f"{base}/chat/completions"
            chat_resp = await client.post(
                chat_url,
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "model": body.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                },
            )
            if chat_resp.status_code == 200:
                return {"available": True}
            data = chat_resp.json() if chat_resp.headers.get("content-type", "").startswith("application/json") else {}
            error = data.get("error", {}).get("message", f"HTTP {chat_resp.status_code}")
            return {"available": False, "error": error}
    except httpx.TimeoutException:
        return {"available": False, "error": "请求超时，请检查网络或 Base URL"}
    except Exception as e:
        return {"available": False, "error": str(e)}
