"""
应用配置
========
从环境变量读取所有配置，支持 .env 文件。
本地开发直接使用默认值即可（SQLite + localhost Redis）。
"""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── OpenAI / 转写 ────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    transcription_model: str = "gpt-4o-transcribe"
    chat_model: str = "gpt-4o"
    max_transcription_workers: int = 20

    # ── 数据库（本地默认 SQLite，生产用 PostgreSQL） ──────────────────────────
    database_url: str = "sqlite:///./data/meeting.db"

    # ── Redis / Celery ───────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── 文件存储 ─────────────────────────────────────────────────────────────
    audio_dir: str = "./data/audio"
    max_upload_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB
    max_recordings_per_meeting: int = 4

    # ── ML 微服务地址 ─────────────────────────────────────────────────────────
    vad_service_url: str = "http://localhost:8001"
    diarization_service_url: str = "http://localhost:8002"

    # ── ModelScope 模型缓存目录 ───────────────────────────────────────────────
    modelscope_cache: str = "./data/models_cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()
