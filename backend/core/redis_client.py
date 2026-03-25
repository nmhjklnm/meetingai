"""
Redis 客户端（用于 Celery broker + 进度缓存）
"""
from __future__ import annotations

import json
import redis

from backend.core.config import get_settings


def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def set_progress(meeting_id: str, data: dict, ttl: int = 3600) -> None:
    """写入处理进度到 Redis，TTL 默认 1 小时"""
    r = get_redis()
    r.setex(f"meeting:{meeting_id}:progress", ttl, json.dumps(data, ensure_ascii=False))


def get_progress(meeting_id: str) -> dict | None:
    """读取进度"""
    r = get_redis()
    raw = r.get(f"meeting:{meeting_id}:progress")
    return json.loads(raw) if raw else None
