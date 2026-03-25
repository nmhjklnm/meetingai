"""
说话人分离微服务 — CAM++ (ModelScope)
======================================
独立进程，模型在服务启动时加载一次，之后常驻内存处理所有请求。

端口:  8002（默认）
接口:
  GET  /health   → {"status": "ok", "model_loaded": true}
  POST /diarize  → multipart:
                     file=<16kHz PCM WAV>
                     segments=<JSON: [{"start":float, "end":float}, ...]>
                     num_speakers=<int|null, 可选>
               ← {"segments": [{"start":float, "end":float, "speaker_id":str}], "num_speakers":int}

启动方式:
  uv run uvicorn ml_services.diarization_service:app --port 8002
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [diar] %(message)s",
)
logger = logging.getLogger("diarization_service")

# ── 全局 pipeline 实例（启动时加载，请求间复用） ──────────────────────────
_pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    logger.info("正在加载 CAM++ 说话人嵌入模型（首次需要从 ModelScope 下载）...")
    from backend.services.diarization.pipeline import DiarizationPipeline, _get_pipeline
    _pipeline = DiarizationPipeline()
    _get_pipeline()       # 确保模型权重已经加载进内存
    logger.info("✓ CAM++ 就绪，等待请求")
    yield
    logger.info("说话人分离服务关闭")


app = FastAPI(title="Diarization Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _pipeline is not None}


@app.post("/diarize")
async def diarize(
    file: Annotated[UploadFile, File(description="16kHz 单声道 PCM WAV")],
    segments: Annotated[str, Form(description='VAD 输出的语音段 JSON，格式 [{"start":0.0,"end":1.5},...]')],
    num_speakers: Annotated[Optional[int], Form()] = None,
):
    """
    对音频进行说话人分离。

    - **file**: 16kHz 单声道 WAV 文件
    - **segments**: VAD 输出的语音段列表（JSON 字符串）
    - **num_speakers**: 说话人数量（不传则自动检测）
    """
    if _pipeline is None:
        raise HTTPException(503, "模型尚未加载")

    try:
        segs_list = json.loads(segments)
        segs = [(s["start"], s["end"]) for s in segs_list]
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(422, f"segments 格式错误: {exc}") from exc

    if not segs:
        raise HTTPException(422, "segments 为空")

    content = await file.read()
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with open(tmp, "wb") as f:
            f.write(content)

        logger.info("开始说话人分离，%d 段，num_speakers=%s", len(segs), num_speakers)
        diarized = _pipeline.diarize(tmp, segs, num_speakers=num_speakers)
        diarized = _pipeline.merge_consecutive(diarized, gap_threshold=1.5)

        unique_speakers = len({d.speaker_id for d in diarized})
        result = [
            {"start": d.start, "end": d.end, "speaker_id": d.speaker_id}
            for d in diarized
        ]
        logger.info("分离完成，%d 段，%d 位说话人", len(result), unique_speakers)
        return {"segments": result, "num_speakers": unique_speakers}

    except Exception as exc:
        logger.exception("说话人分离异常")
        raise HTTPException(500, str(exc)) from exc
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
