"""
Redis 客户端（用于 Celery broker + 进度缓存）
"""
from __future__ import annotations

import json
from functools import lru_cache

import redis

from backend.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def _progress_key(meeting_id: str, suffix: str = "") -> str:
    return f"meeting:{meeting_id}:progress{':' + suffix if suffix else ''}"


def set_progress(meeting_id: str, data: dict, ttl: int = 3600, suffix: str = "") -> None:
    get_redis().setex(_progress_key(meeting_id, suffix), ttl, json.dumps(data, ensure_ascii=False))


def get_progress(meeting_id: str, suffix: str = "") -> dict | None:
    raw = get_redis().get(_progress_key(meeting_id, suffix))
    return json.loads(raw) if raw else None
