"""
VAD 微服务 — FSMN-VAD (ModelScope)
====================================
独立进程，模型在服务启动时加载一次，之后常驻内存处理所有请求。

端口:  8001（默认）
接口:
  GET  /health   → {"status": "ok", "model_loaded": true}
  POST /detect   → multipart: file=<16kHz PCM WAV>, min_speech_ms=<int=200>
               ← {"segments": [{"start": float, "end": float}], "count": int}

启动方式:
  uv run uvicorn ml_services.vad_service:app --port 8001
"""
from __future__ import annotations

import logging
import os
import tempfile
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [vad] %(message)s",
)
logger = logging.getLogger("vad_service")

# ── 全局模型实例（启动时加载，请求间复用） ────────────────────────────────
_detector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _detector
    logger.info("正在加载 FSMN-VAD 模型（首次需要从 ModelScope 下载）...")
    # 导入并实例化，同时触发底层模型加载
    from backend.services.vad.detector import VADDetector, _get_model
    _detector = VADDetector(min_speech_ms=200)
    _get_model()          # 确保模型权重已经加载进内存
    logger.info("✓ FSMN-VAD 就绪，等待请求")
    yield
    logger.info("VAD 服务关闭")


app = FastAPI(title="VAD Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _detector is not None}


@app.post("/detect")
async def detect(
    file: Annotated[UploadFile, File(description="16kHz 单声道 PCM WAV")],
    min_speech_ms: Annotated[int, Form()] = 200,
):
    """
    检测音频中的语音段。

    - **file**: 16kHz 单声道 WAV 文件
    - **min_speech_ms**: 最小语音段长度（毫秒），默认 200ms
    """
    if _detector is None:
        raise HTTPException(503, "模型尚未加载")

    content = await file.read()
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with open(tmp, "wb") as f:
            f.write(content)

        from backend.services.vad.detector import VADDetector
        local_detector = VADDetector(min_speech_ms=min_speech_ms)
        segments = local_detector.detect(tmp)

        result = [{"start": s.start, "end": s.end} for s in segments]
        logger.info("VAD 完成，检测到 %d 段语音", len(result))
        return {"segments": result, "count": len(result)}

    except Exception as exc:
        logger.exception("VAD 处理异常")
        raise HTTPException(500, str(exc)) from exc
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
