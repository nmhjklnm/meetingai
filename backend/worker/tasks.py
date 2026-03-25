"""
Celery 异步任务
===============
音频处理完整 Pipeline（6 步）：
  1. merge        — 读取 DB 录音列表，ffmpeg 合并/转换 → 16kHz 单声道 WAV
  2. vad          — HTTP 调用 VAD 微服务 (localhost:8001)
  3. diarization  — HTTP 调用 Diarization 微服务 (localhost:8002)
  4. transcription— 并发转写（GPT-4o-transcribe，Semaphore 控制）
  5. nlp          — NLP 分析（GPT-4o 摘要 + 行动项）
  6. save         — 清旧数据 → 批量插入 → Meeting.status='done'

Worker 进程本身不加载任何 ML 模型（torch/funasr/modelscope），
所有模型推理均通过 HTTP 调用独立的 ML 微服务完成。
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
from celery import Celery

from backend.core.config import get_settings
from backend.core.redis_client import set_progress

settings = get_settings()

celery_app = Celery(
    "meeting_transcriber",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


# ── 进度上报 ──────────────────────────────────────────────────────────────────

STEP_NAMES = {
    1: "merge",
    2: "vad",
    3: "diarization",
    4: "transcription",
    5: "nlp",
    6: "save",
}


def _report(
    meeting_id: str,
    step: int,
    total: int,
    step_name: str,
    message: str,
    status: str = "processing",
    sub_done: int | None = None,
    sub_total: int | None = None,
    eta_seconds: int | None = None,
) -> None:
    """
    写入 Redis 进度。支持子进度（sub_done/sub_total）和预计剩余时间（eta_seconds）。
    percent 在 step 内部按子进度线性插值，保证前端看到的是连续推进的百分比。
    """
    if sub_done is not None and sub_total and sub_total > 0:
        pct = int(((step - 1 + sub_done / sub_total) / total) * 100)
    else:
        pct = int((step - 1) / total * 100)

    eta_str = ""
    if eta_seconds is not None and eta_seconds > 5:
        m, s = divmod(eta_seconds, 60)
        eta_str = f"，预计剩余 {m}分{s:02d}秒" if m > 0 else f"，预计剩余 {s}秒"

    set_progress(meeting_id, {
        "step": step,
        "step_name": step_name,
        "total_steps": total,
        "message": message + eta_str,
        "percent": min(pct, 99),
        "status": status,
        **({"sub_done": sub_done, "sub_total": sub_total} if sub_done is not None else {}),
    })


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _fmt_ts(seconds: float) -> str:
    """秒数 → [MM:SS] 格式"""
    m, s = divmod(int(seconds), 60)
    return f"[{m:02d}:{s:02d}]"


def _get_audio_duration(wav_path: str) -> float:
    """读取 WAV 时长（秒）"""
    import wave
    with wave.open(wav_path, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def _merge_recordings(file_paths: list[str], output_path: str) -> str:
    """
    将一条或多条录音合并为单个 16kHz 单声道 WAV。
    单条录音直接格式转换；多条使用 ffmpeg concat demuxer。
    """
    if len(file_paths) == 1:
        subprocess.run(
            ["ffmpeg", "-y", "-i", file_paths[0],
             "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", output_path],
            check=True, capture_output=True,
        )
        return output_path

    # Multiple files: concat
    fd, list_file = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        with open(list_file, "w") as f:
            for fpath in file_paths:
                safe_path = fpath.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
             "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", output_path],
            check=True, capture_output=True,
        )
    finally:
        os.unlink(list_file)
    return output_path


# ── ML 服务调用（HTTP） ────────────────────────────────────────────────────────

def _call_vad(wav_path: str, min_speech_ms: int = 1500) -> list[dict]:
    """调用 VAD 微服务，返回 [{"start": float, "end": float}]"""
    url = f"{settings.vad_service_url}/detect"
    with open(wav_path, "rb") as f:
        resp = httpx.post(
            url,
            files={"file": ("audio.wav", f, "audio/wav")},
            data={"min_speech_ms": min_speech_ms},
            timeout=600,
        )
    resp.raise_for_status()
    return resp.json()["segments"]


def _call_diarization(
    wav_path: str,
    segments: list[dict],
    num_speakers: int | None = None,
) -> list[dict]:
    """调用说话人分离微服务，返回 [{"start", "end", "speaker_id"}]"""
    url = f"{settings.diarization_service_url}/diarize"
    data: dict = {"segments": json.dumps(segments)}
    if num_speakers is not None:
        data["num_speakers"] = num_speakers
    with open(wav_path, "rb") as f:
        resp = httpx.post(
            url,
            files={"file": ("audio.wav", f, "audio/wav")},
            data=data,
            timeout=3600,
        )
    resp.raise_for_status()
    return resp.json()["segments"]


# ── 主 Celery 任务 ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="backend.worker.tasks.process_meeting_task")
def process_meeting_task(
    self,
    meeting_id: str,
    context: str | None = None,
    chat_model: str | None = None,
    transcription_model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict:
    """
    主处理任务。6 步 Pipeline，进度实时写入 Redis。
    从数据库读取 meeting.recordings，合并后依次执行 VAD → 说话人分离 → 转写 → NLP → 保存。
    """
    from backend.core.database import get_session_factory
    from backend.models.meeting import Meeting, Recording, Segment, Speaker
    from backend.services.transcription.transcriber import TranscriptionService, DEFAULT_PROMPT
    from backend.services.nlp.processor import NLPService

    TOTAL_STEPS = 6

    def _fail(msg: str):
        _report(meeting_id, 1, TOTAL_STEPS, "error", f"失败: {msg}", "failed")
        factory = get_session_factory()
        db = factory()
        try:
            m = db.get(Meeting, meeting_id)
            if m:
                m.status = "failed"
                m.error_message = msg
                db.commit()
        finally:
            db.close()

    try:
        # ── Step 1: merge — 读取录音并合并 ──────────────────────────────────
        _report(meeting_id, 1, TOTAL_STEPS, "merge", "正在读取录音并合并...")

        factory = get_session_factory()
        db = factory()
        try:
            meeting = db.get(Meeting, meeting_id)
            if not meeting:
                _fail("会议记录不存在")
                return {"status": "failed", "reason": "meeting not found"}

            recordings = sorted(meeting.recordings, key=lambda r: r.order)
            if not recordings:
                _fail("该会议没有上传录音文件")
                return {"status": "failed", "reason": "no recordings"}

            # 提取文件路径（避免 session 关闭后 DetachedInstanceError）
            recording_paths = [r.file_path for r in recordings]

            meeting.status = "processing"
            db.commit()
        finally:
            db.close()

        # Output path: {audio_dir}/{meeting_id}_merged.wav
        audio_dir = settings.audio_dir
        os.makedirs(audio_dir, exist_ok=True)
        merged_wav = os.path.join(audio_dir, f"{meeting_id}_merged.wav")

        try:
            _merge_recordings(recording_paths, merged_wav)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            _fail(f"ffmpeg 合并/转换失败: {stderr[:200]}")
            return {"status": "failed"}

        duration = _get_audio_duration(merged_wav)
        _report(meeting_id, 1, TOTAL_STEPS, "merge",
                f"音频合并完成（{duration/60:.1f} 分钟）",
                sub_done=1, sub_total=1)

        # ── Step 2: vad — 语音活动检测 ──────────────────────────────────────
        vad_eta = max(10, int(duration * 0.006))
        _report(meeting_id, 2, TOTAL_STEPS, "vad",
                f"语音活动检测（音频 {duration/60:.1f} 分钟）",
                eta_seconds=vad_eta)
        t_vad = time.time()
        try:
            speech_segs = _call_vad(merged_wav, min_speech_ms=1500)
        except httpx.HTTPError as e:
            _fail(f"VAD 服务调用失败: {e}（请确认 VAD 服务已启动: {settings.vad_service_url}）")
            return {"status": "failed"}

        if not speech_segs:
            _fail("未检测到有效语音段，请确认音频文件正常")
            return {"status": "failed"}

        vad_elapsed = time.time() - t_vad

        # ── Step 3: diarization — 说话人分离 ────────────────────────────────
        n_segs = len(speech_segs)
        diar_eta = max(30, int(n_segs * 0.06))
        _report(meeting_id, 3, TOTAL_STEPS, "diarization",
                f"说话人分离（{n_segs} 段）",
                eta_seconds=diar_eta)
        t_diar = time.time()
        try:
            raw_diarized = _call_diarization(merged_wav, speech_segs)
        except httpx.HTTPError as e:
            _fail(f"说话人分离服务调用失败: {e}（请确认服务已启动: {settings.diarization_service_url}）")
            return {"status": "failed"}

        diar_elapsed = time.time() - t_diar

        # 统一字段名：diarization 服务返回 speaker_id，转写/NLP 用 speaker
        diarized_segs = [
            {"start": s["start"], "end": s["end"], "speaker": s["speaker_id"]}
            for s in raw_diarized
        ]
        num_speakers = len({d["speaker"] for d in diarized_segs})

        # ── Step 4: transcription — 并发转写 ───────────────────────────────
        n_trans = len(diarized_segs)
        trans_eta = max(30, int(n_trans / 20))
        _report(meeting_id, 4, TOTAL_STEPS, "transcription",
                f"转写（{n_trans} 段，{num_speakers} 位说话人）",
                eta_seconds=trans_eta)

        prompt = DEFAULT_PROMPT + f"\n补充背景：{context}" if context else DEFAULT_PROMPT

        transcriber = TranscriptionService(
            base_url=base_url or settings.openai_base_url,
            api_key=api_key or settings.openai_api_key,
            model=transcription_model or settings.transcription_model,
            max_workers=settings.max_transcription_workers,
            prompt=prompt,
        )

        # 子进度回调
        t_trans = time.time()
        _trans_done = [0]

        async def _on_transcription_progress(_idx: int, _total: int, _result: dict) -> None:
            _trans_done[0] += 1
            elapsed = time.time() - t_trans
            rate = _trans_done[0] / elapsed if elapsed > 0.1 else 0.1
            eta = int((_total - _trans_done[0]) / rate)
            _report(
                meeting_id, 4, TOTAL_STEPS, "transcription",
                f"转写 {_trans_done[0]}/{_total} 段",
                sub_done=_trans_done[0],
                sub_total=_total,
                eta_seconds=max(0, eta),
            )

        transcribed = asyncio.run(
            transcriber.transcribe_batch(merged_wav, diarized_segs,
                                         on_progress=_on_transcription_progress)
        )

        # ── Step 5: nlp — AI 分析 ──────────────────────────────────────────
        _report(meeting_id, 5, TOTAL_STEPS, "nlp", "AI 摘要生成", eta_seconds=30)

        full_transcript = "\n".join(
            f"{_fmt_ts(r['start'])} {r['speaker']}: {r.get('text', '')}"
            for r in transcribed
            if r.get("text") and "[ERROR" not in r.get("text", "")
        )

        summary_data: dict = {}
        if full_transcript.strip():
            nlp = NLPService(
                base_url=base_url or settings.openai_base_url,
                api_key=api_key or settings.openai_api_key,
                model=chat_model or settings.chat_model,
            )
            try:
                summary_data = nlp.analyze(full_transcript)
            except Exception as e:
                summary_data = {"error": str(e), "raw_transcript": full_transcript[:500]}

        # ── Step 6: save — 保存到数据库 ─────────────────────────────────────
        _report(meeting_id, 6, TOTAL_STEPS, "save", "保存结果...")

        factory = get_session_factory()
        db = factory()
        try:
            meeting = db.get(Meeting, meeting_id)
            if not meeting:
                return {"status": "failed", "reason": "meeting not found in DB"}

            # 清除旧数据
            db.query(Segment).filter(Segment.meeting_id == meeting_id).delete()
            db.query(Speaker).filter(Speaker.meeting_id == meeting_id).delete()

            # 更新会议信息
            meeting.status = "done"
            meeting.audio_duration = duration
            meeting.num_speakers = num_speakers
            meeting.summary = summary_data

            # 批量插入 segments
            for r in transcribed:
                db.add(Segment(
                    meeting_id=meeting_id,
                    start=r["start"],
                    end=r["end"],
                    speaker_id=r["speaker"],
                    text=r.get("text", ""),
                ))

            # 批量插入 speakers（初始显示名用中文"说话人 A"）
            unique_speakers = {r["speaker"] for r in transcribed}
            for spk in sorted(unique_speakers):
                # "Speaker A" → "说话人 A"
                display = spk.replace("Speaker ", "说话人 ") if spk.startswith("Speaker ") else spk
                db.add(Speaker(
                    meeting_id=meeting_id,
                    speaker_id=spk,
                    name=display,
                ))

            db.commit()
        finally:
            db.close()

        set_progress(meeting_id, {
            "step": TOTAL_STEPS,
            "step_name": "done",
            "total_steps": TOTAL_STEPS,
            "message": "处理完成！",
            "percent": 100,
            "status": "done",
        })
        return {"status": "done", "meeting_id": meeting_id}

    except Exception as exc:  # noqa: E722
        import traceback
        err_msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-800:]}"
        _fail(err_msg)
        return {"status": "failed", "error": str(exc)}


# ── 辅助：构建带时间戳的全文 ─────────────────────────────────────────────────

def _build_transcript(meeting_id: str) -> tuple[str, dict]:
    """从 DB 读取 segments + speakers，构建带时间戳的全文。返回 (transcript, spk_map)。"""
    from backend.core.database import get_session_factory
    from backend.models.meeting import Meeting, Segment

    factory = get_session_factory()
    db = factory()
    try:
        meeting = db.get(Meeting, meeting_id)
        if not meeting:
            return "", {}
        spk_map = {s.speaker_id: s.name for s in meeting.speakers}
        segments = db.query(Segment).filter(
            Segment.meeting_id == meeting_id
        ).order_by(Segment.start).all()

        transcript = "\n".join(
            f"{_fmt_ts(seg.start)} {spk_map.get(seg.speaker_id, seg.speaker_id)}: {seg.text}"
            for seg in segments
            if seg.text and "[ERROR" not in seg.text
        )
        return transcript, spk_map
    finally:
        db.close()


# ── 重新生成时间轴 ───────────────────────────────────────────────────────────

TIMELINE_PROMPT = """\
你是一位会议记录分析助手。请根据以下带时间戳的会议转录文本，提炼出会议的 **Topic 时间轴**（议题主线）。

要求：
- 按时间顺序列出会议中讨论的各个 topic（议题/话题）
- 每个 topic 用一句话概括核心内容，体现这一阶段在聊什么
- 相邻时间如果在聊同一个话题则合并，不要重复
- 覆盖整个会议时长，不遗漏重要议题转换点
- 通常 5-15 个节点（视会议长度而定）
- time 字段为该 topic 开始的秒数（从转录文本的 [MM:SS] 时间标记推算）

转录文本：
{transcript}

请用 JSON 格式返回：
{{"timeline": [{{"time": 0, "title": "该阶段讨论的核心话题"}}]}}
"""


SUMMARY_ONLY_PROMPT = """\
你是一位会议记录整理助手。请根据以下会议转录文本，完成以下任务：

1. **整体摘要**（200字以内）：概括会议核心议题和结论
2. **各说话人发言要点**：每位说话人 3-5 条要点
3. **行动项**：列出所有明确的任务、承诺或下一步行动，注明负责人
4. **关键词**：5-10 个会议相关关键词

转录文本：
{transcript}

请用 JSON 格式返回：
{{
  "summary": "...",
  "speakers": {{"说话人名": ["要点1", "要点2"], ...}},
  "action_items": [{{"assignee": "...", "task": "...", "deadline": "..."}}],
  "keywords": ["...", "..."]
}}
"""


def _run_regen(
    meeting_id: str,
    tag: str,
    prompt: str,
    merge_fn,  # (old_summary: dict, ai_result: dict) -> dict
    chat_model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict:
    """共享的重新生成逻辑：调 AI → 合并写入 DB → 更新进度。"""
    import json as _json
    from backend.core.database import get_session_factory
    from backend.models.meeting import Meeting
    from openai import OpenAI

    set_progress(meeting_id, {
        "message": f"正在生成{tag}...", "percent": 20, "status": "processing",
    }, suffix=tag)

    transcript, _ = _build_transcript(meeting_id)
    if not transcript.strip():
        set_progress(meeting_id, {"status": "done", "message": "无转录文本", "percent": 100}, suffix=tag)
        return {"status": "failed", "reason": "empty transcript"}

    client = OpenAI(
        base_url=base_url or settings.openai_base_url,
        api_key=api_key or settings.openai_api_key,
    )
    try:
        resp = client.chat.completions.create(
            model=chat_model or settings.chat_model,
            messages=[{"role": "user", "content": prompt.format(transcript=transcript)}],
            response_format={"type": "json_object"},
        )
        ai_result = _json.loads(resp.choices[0].message.content)
    except Exception as e:
        set_progress(meeting_id, {"status": "done", "message": f"失败: {e}", "percent": 100}, suffix=tag)
        return {"status": "failed", "error": str(e)}

    factory = get_session_factory()
    db = factory()
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting:
            meeting.summary = merge_fn(dict(meeting.summary or {}), ai_result)
            db.commit()
    finally:
        db.close()

    set_progress(meeting_id, {"status": "done", "message": f"{tag}已更新！", "percent": 100}, suffix=tag)
    return {"status": "done", "meeting_id": meeting_id}


@celery_app.task(bind=True, name="backend.worker.tasks.regenerate_timeline_task")
def regenerate_timeline_task(self, meeting_id: str, chat_model: str | None = None,
                             api_key: str | None = None, base_url: str | None = None) -> dict:
    def merge(old, new):
        old["timeline"] = new.get("timeline", [])
        return old
    return _run_regen(meeting_id, "时间轴", TIMELINE_PROMPT, merge, chat_model, api_key, base_url)


@celery_app.task(bind=True, name="backend.worker.tasks.regenerate_summary_task")
def regenerate_summary_task(self, meeting_id: str, chat_model: str | None = None,
                            api_key: str | None = None, base_url: str | None = None) -> dict:
    def merge(old, new):
        # 保留时间轴不变
        tl = old.get("timeline")
        if tl:
            new["timeline"] = tl
        return new
    return _run_regen(meeting_id, "纪要", SUMMARY_ONLY_PROMPT, merge, chat_model, api_key, base_url)
