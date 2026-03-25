"""
会议 REST API
=============
POST   /api/meetings                          创建会议（草稿）
GET    /api/meetings                          获取历史会议列表
GET    /api/meetings/{id}                     获取会议详情 + 录音 + 转录 + 说话人
DELETE /api/meetings/{id}                     删除会议
POST   /api/meetings/{id}/recordings          上传录音文件
DELETE /api/meetings/{id}/recordings/{rid}    删除录音
POST   /api/meetings/{id}/process             启动处理（draft/failed）
PATCH  /api/meetings/{id}/speakers            重命名说话人
GET    /api/meetings/{id}/export/srt          导出 SRT
GET    /api/meetings/{id}/export/txt          导出 TXT
GET    /api/meetings/{id}/export/summary      导出会议纪要
"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.models.meeting import Meeting, Recording, Segment, Speaker

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CreateMeetingRequest(BaseModel):
    title: str = "未命名会议"


class UpdateMeetingRequest(BaseModel):
    title: Optional[str] = None


class ProcessRequest(BaseModel):
    context: Optional[str] = None
    chat_model: Optional[str] = None
    transcription_model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class SpeakerUpdateItem(BaseModel):
    speaker_id: str
    name: str


class SpeakerUpdateRequest(BaseModel):
    speakers: list[SpeakerUpdateItem]


class RecordingOut(BaseModel):
    id: int
    meeting_id: str
    filename: str
    file_path: str
    file_size: int
    duration: Optional[float]
    order: int
    uploaded_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_instance(cls, rec: Recording) -> RecordingOut:
        return cls(
            id=rec.id,
            meeting_id=rec.meeting_id,
            filename=rec.filename,
            file_path=rec.file_path,
            file_size=rec.file_size,
            duration=rec.duration,
            order=rec.order,
            uploaded_at=rec.uploaded_at.isoformat() if rec.uploaded_at else "",
        )


class SegmentOut(BaseModel):
    id: int
    start: float
    end: float
    speaker_id: str
    speaker_name: str
    text: Optional[str]

    model_config = {"from_attributes": True}


class SpeakerOut(BaseModel):
    speaker_id: str
    name: str

    model_config = {"from_attributes": True}


class MeetingOut(BaseModel):
    id: str
    title: str
    status: str
    audio_duration: Optional[float]
    num_speakers: Optional[int]
    created_at: str
    summary: Optional[dict] = None
    error_message: Optional[str] = None
    speakers: list[SpeakerOut] = []
    segments: list[SegmentOut] = []
    recordings: list[RecordingOut] = []

    model_config = {"from_attributes": True}


class MeetingListItem(BaseModel):
    id: str
    title: str
    status: str
    audio_duration: Optional[float]
    num_speakers: Optional[int]
    created_at: str
    recording_count: int = 0
    total_duration: float = 0.0

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_meeting_or_404(meeting_id: str, db: Session) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    return meeting


def _speaker_map(meeting: Meeting) -> dict[str, str]:
    return {s.speaker_id: s.name for s in meeting.speakers}


def _build_meeting_out(meeting: Meeting) -> dict:
    spk_map = _speaker_map(meeting)
    return {
        "id": meeting.id,
        "title": meeting.title,
        "status": meeting.status,
        "audio_duration": meeting.audio_duration,
        "num_speakers": meeting.num_speakers,
        "created_at": meeting.created_at.isoformat(),
        "summary": meeting.summary,
        "error_message": meeting.error_message,
        "speakers": [
            {"speaker_id": s.speaker_id, "name": s.name}
            for s in meeting.speakers
        ],
        "segments": [
            {
                "id": seg.id,
                "start": seg.start,
                "end": seg.end,
                "speaker_id": seg.speaker_id,
                "speaker_name": spk_map.get(seg.speaker_id, seg.speaker_id),
                "text": seg.text,
            }
            for seg in meeting.segments
        ],
        "recordings": [
            RecordingOut.from_orm_instance(rec).model_dump()
            for rec in meeting.recordings
        ],
    }


def _get_duration_ffprobe(filepath: str) -> Optional[float]:
    """Use ffprobe to get audio duration in seconds."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, OSError):
        pass
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

# POST /api/meetings — Create meeting (draft)
@router.post("", status_code=status.HTTP_201_CREATED)
def create_meeting(
    body: CreateMeetingRequest,
    db: Session = Depends(get_db),
):
    """创建会议（草稿状态）"""
    meeting_id = str(uuid.uuid4())
    title = body.title.strip() or "未命名会议"

    meeting = Meeting(
        id=meeting_id,
        title=title,
        status="draft",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    return _build_meeting_out(meeting)


# GET /api/meetings — List all meetings
@router.get("")
def list_meetings(db: Session = Depends(get_db)):
    """返回所有会议，按创建时间倒序"""
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    result = []
    for m in meetings:
        recording_count = len(m.recordings)
        total_duration = sum(
            (r.duration or 0.0) for r in m.recordings
        )
        result.append({
            "id": m.id,
            "title": m.title,
            "status": m.status,
            "audio_duration": m.audio_duration,
            "num_speakers": m.num_speakers,
            "created_at": m.created_at.isoformat(),
            "recording_count": recording_count,
            "total_duration": total_duration,
        })
    return result


# GET /api/meetings/{id} — Meeting detail
@router.get("/{meeting_id}")
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    """返回会议详情（含录音、转录片段、说话人）"""
    meeting = _get_meeting_or_404(meeting_id, db)
    return _build_meeting_out(meeting)


# PATCH /api/meetings/{id} — Update meeting
@router.patch("/{meeting_id}")
def update_meeting(
    meeting_id: str,
    body: UpdateMeetingRequest,
    db: Session = Depends(get_db),
):
    """更新会议信息（标题等）"""
    meeting = _get_meeting_or_404(meeting_id, db)
    if body.title is not None:
        meeting.title = body.title.strip() or meeting.title
    db.commit()
    return _build_meeting_out(meeting)


# DELETE /api/meetings/{id} — Delete meeting
@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    """删除会议及所有关联数据和文件"""
    meeting = _get_meeting_or_404(meeting_id, db)
    settings = get_settings()

    # Delete the meeting's audio directory (contains all recordings)
    meeting_dir = Path(settings.audio_dir) / meeting_id
    if meeting_dir.exists():
        try:
            shutil.rmtree(meeting_dir)
        except OSError:
            pass

    db.delete(meeting)
    db.commit()


# POST /api/meetings/{id}/recordings — Upload recording
@router.post("/{meeting_id}/recordings", status_code=status.HTTP_201_CREATED)
async def upload_recording(
    meeting_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传录音文件到指定会议"""
    meeting = _get_meeting_or_404(meeting_id, db)
    settings = get_settings()

    # Validate meeting status
    if meeting.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"只能在草稿状态上传录音（当前状态: {meeting.status}）",
        )

    # Validate recording count
    if len(meeting.recordings) >= settings.max_recordings_per_meeting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"每个会议最多 {settings.max_recordings_per_meeting} 个录音",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="文件超过 2GB 限制",
        )

    # Determine filename and save path
    original_name = file.filename or "recording"
    filename = original_name
    meeting_dir = Path(settings.audio_dir) / meeting_id
    meeting_dir.mkdir(parents=True, exist_ok=True)
    file_path = meeting_dir / filename

    # Handle duplicate filenames
    if file_path.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while file_path.exists():
            filename = f"{stem}_{counter}{suffix}"
            file_path = meeting_dir / filename
            counter += 1

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Get audio duration via ffprobe
    duration = _get_duration_ffprobe(str(file_path))

    # Determine order
    max_order = max((r.order for r in meeting.recordings), default=-1)
    new_order = max_order + 1

    # Create recording record
    recording = Recording(
        meeting_id=meeting_id,
        filename=filename,
        file_path=str(file_path),
        file_size=len(content),
        duration=duration,
        order=new_order,
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)

    return RecordingOut.from_orm_instance(recording).model_dump()


# DELETE /api/meetings/{id}/recordings/{rid} — Delete recording
@router.delete(
    "/{meeting_id}/recordings/{recording_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_recording(
    meeting_id: str,
    recording_id: int,
    db: Session = Depends(get_db),
):
    """删除指定录音"""
    meeting = _get_meeting_or_404(meeting_id, db)

    recording = db.get(Recording, recording_id)
    if not recording or recording.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="录音不存在")

    # Delete file
    if recording.file_path and os.path.exists(recording.file_path):
        try:
            os.remove(recording.file_path)
        except OSError:
            pass

    db.delete(recording)
    db.commit()


# POST /api/meetings/{id}/process — Start processing
@router.post("/{meeting_id}/process", status_code=status.HTTP_202_ACCEPTED)
def start_processing(
    meeting_id: str,
    body: ProcessRequest = ProcessRequest(),
    db: Session = Depends(get_db),
):
    """启动会议处理（仅 draft/failed 状态可操作）"""
    meeting = _get_meeting_or_404(meeting_id, db)

    if meeting.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"只能处理草稿或失败状态的会议（当前状态: {meeting.status}）",
        )

    if not meeting.recordings:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="至少需要上传一个录音才能开始处理",
        )

    # Update status
    meeting.status = "processing"
    meeting.error_message = None
    db.commit()

    # Submit Celery task
    from backend.worker.tasks import process_meeting_task
    process_meeting_task.delay(
        meeting_id,
        body.context,
        body.chat_model,
        body.transcription_model,
        body.api_key,
        body.base_url,
    )

    return {"id": meeting_id, "status": "processing"}


# PATCH /api/meetings/{id}/speakers — Rename speakers
@router.patch("/{meeting_id}/speakers")
def update_speakers(
    meeting_id: str,
    body: SpeakerUpdateRequest,
    db: Session = Depends(get_db),
):
    """更新说话人姓名映射"""
    meeting = _get_meeting_or_404(meeting_id, db)

    existing = {s.speaker_id: s for s in meeting.speakers}
    for item in body.speakers:
        if item.speaker_id in existing:
            existing[item.speaker_id].name = item.name
        else:
            db.add(Speaker(
                meeting_id=meeting_id,
                speaker_id=item.speaker_id,
                name=item.name,
            ))
    db.commit()
    return {"ok": True}


# GET /api/meetings/{id}/export/srt — Export SRT
@router.get("/{meeting_id}/export/srt")
def export_srt(meeting_id: str, db: Session = Depends(get_db)):
    """导出 SRT 字幕"""
    meeting = _get_meeting_or_404(meeting_id, db)
    spk_map = _speaker_map(meeting)

    def _sec_to_srt(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec % 1) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, seg in enumerate(meeting.segments, 1):
        if not seg.text:
            continue
        speaker_name = spk_map.get(seg.speaker_id, seg.speaker_id)
        lines.append(
            f"{i}\n{_sec_to_srt(seg.start)} --> {_sec_to_srt(seg.end)}\n"
            f"{speaker_name}: {seg.text}\n"
        )

    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{meeting_id}.srt"'
        },
    )


# GET /api/meetings/{id}/export/txt — Export TXT
@router.get("/{meeting_id}/export/txt")
def export_txt(meeting_id: str, db: Session = Depends(get_db)):
    """导出纯文本"""
    meeting = _get_meeting_or_404(meeting_id, db)
    spk_map = _speaker_map(meeting)

    lines = [f"# {meeting.title}", ""]
    for seg in meeting.segments:
        if not seg.text:
            continue
        speaker_name = spk_map.get(seg.speaker_id, seg.speaker_id)
        m = int(seg.start // 60)
        s = int(seg.start % 60)
        lines.append(f"[{m:02d}:{s:02d}] {speaker_name}: {seg.text}")

    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{meeting_id}.txt"'
        },
    )


# GET /api/meetings/{id}/export/summary — Export meeting minutes
@router.get("/{meeting_id}/export/summary")
def export_summary(meeting_id: str, db: Session = Depends(get_db)):
    """导出会议纪要（Markdown 格式）"""
    meeting = _get_meeting_or_404(meeting_id, db)

    if meeting.status != "done":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"会议尚未处理完成（状态: {meeting.status}）",
        )

    summary = meeting.summary or {}
    parts = [f"# {meeting.title} — 会议纪要", ""]

    # Summary
    summary_text = summary.get("summary", "")
    if summary_text:
        parts.append("## 摘要")
        parts.append(summary_text)
        parts.append("")

    # Keywords
    keywords = summary.get("keywords", [])
    if keywords:
        parts.append("## 关键词")
        if isinstance(keywords, list):
            parts.append("、".join(keywords))
        else:
            parts.append(str(keywords))
        parts.append("")

    # Action items
    action_items = summary.get("action_items", [])
    if action_items:
        parts.append("## 行动项")
        for item in action_items:
            assignee = item.get("assignee", "未分配")
            task = item.get("task", "")
            deadline = item.get("deadline", "")
            if deadline:
                parts.append(f"- {assignee}：{task}（截止：{deadline}）")
            else:
                parts.append(f"- {assignee}：{task}")
        parts.append("")

    # Per-speaker highlights
    speaker_highlights = summary.get("speakers", {})
    if speaker_highlights:
        parts.append("## 各说话人要点")
        # speaker_highlights could be dict or list
        if isinstance(speaker_highlights, dict):
            for speaker_name, points in speaker_highlights.items():
                parts.append(f"### {speaker_name}")
                if isinstance(points, list):
                    for point in points:
                        parts.append(f"- {point}")
                else:
                    parts.append(f"- {points}")
                parts.append("")
        elif isinstance(speaker_highlights, list):
            for entry in speaker_highlights:
                name = entry.get("name", entry.get("speaker_id", "Unknown"))
                points = entry.get("points", entry.get("highlights", []))
                parts.append(f"### {name}")
                if isinstance(points, list):
                    for point in points:
                        parts.append(f"- {point}")
                else:
                    parts.append(f"- {points}")
                parts.append("")

    content = "\n".join(parts)

    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{meeting_id}_summary.md"'
        },
    )
