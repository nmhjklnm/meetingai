"""
数据库模型
==========
Meeting   — 会议主表
Recording — 音频录音文件（一次会议可有多段）
Segment   — 转录片段（含说话人 + 文本）
Speaker   — 说话人姓名映射（Speaker A → 张三）
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名会议")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )
    # draft | pending | processing | done | failed

    audio_duration: Mapped[Optional[float]] = mapped_column(Float)  # 秒
    num_speakers: Mapped[Optional[int]] = mapped_column(Integer)

    # AI 分析结果（JSON）
    summary: Mapped[Optional[dict]] = mapped_column(JSON)
    # {summary, speakers, action_items, keywords}

    error_message: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    recordings: Mapped[list[Recording]] = relationship(
        "Recording",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="Recording.order",
    )
    segments: Mapped[list[Segment]] = relationship(
        "Segment",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="Segment.start",
    )
    speakers: Mapped[list[Speaker]] = relationship(
        "Speaker", back_populates="meeting", cascade="all, delete-orphan"
    )


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration: Mapped[Optional[float]] = mapped_column(Float)
    order: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="recordings")


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    start: Mapped[float] = mapped_column(Float, nullable=False)
    end: Mapped[float] = mapped_column(Float, nullable=False)
    speaker_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # "Speaker A" / "Speaker B" 等，由说话人分离产生
    text: Mapped[Optional[str]] = mapped_column(Text)

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="segments")


class Speaker(Base):
    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    speaker_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # "Speaker A"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 用户自定义的真实姓名，初始值 = speaker_id

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="speakers")
