"""
数据库会话管理（同步 SQLAlchemy）
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    kwargs: dict = {"pool_pre_ping": True}
    if not settings.database_url.startswith("sqlite"):
        kwargs.update(pool_size=5, max_overflow=10)
    return create_engine(settings.database_url, **kwargs)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker:
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db():
    """FastAPI 依赖注入 — 获取数据库会话"""
    db: Session = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass
