"""
转写服务 — 基于 OpenAI-compatible API（GPT-4o-transcribe）
----------------------------------------------------------
沿用当前已验证的方案，重构为可注入的 Service 类：
  · AsyncOpenAI 并发调用
  · Semaphore 控制并发数
  · 指数退避自动重试（3次）
  · 上下文 prompt 传递（Pass 1 + Pass 2 边界修正）
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI


class TranscriptionService:
    """
    转写服务。

    核心逻辑从 transcribe_diarize.py 中提取，解耦为独立服务。
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-transcribe",
        max_workers: int = 20,
        max_retries: int = 3,
    ):
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.max_workers = max_workers
        self.max_retries = max_retries

        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        return self._client

    async def transcribe_segment(
        self,
        wav_path: str | Path,
        start: float,
        end: float,
        prompt: str = "",
        retries: int = 3,
    ) -> str:
        """
        转写单个语音段，自动剪切 + 调用 API + 重试。

        从 transcribe_diarize.py 的 _transcribe_one() 提取。
        """
        import subprocess

        client = self._get_client()
        loop = asyncio.get_event_loop()

        for attempt in range(retries):
            if attempt > 0:
                await asyncio.sleep(2 ** attempt)

            # 剪切片段
            tmp = tempfile.mktemp(suffix=".wav")
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["ffmpeg", "-y", "-i", str(wav_path),
                     "-ss", str(start), "-to", str(end),
                     "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", tmp],
                    check=True, capture_output=True,
                ),
            )

            try:
                with open(tmp, "rb") as f:
                    resp = await client.audio.transcriptions.create(
                        model=self.model,
                        file=f,
                        response_format="text",
                        extra_body={"prompt": prompt} if prompt else {},
                    )
                return (getattr(resp, "text", None) or str(resp)).strip()
            except Exception as exc:
                if attempt == retries - 1:
                    return f"[ERROR: {exc}]"
            finally:
                try:
                    import os as _os
                    _os.unlink(tmp)
                except OSError:
                    pass
        return ""

    async def transcribe_batch(
        self,
        wav_path: str | Path,
        segments: list[dict],   # [{"start": 0.5, "end": 3.2, "speaker": "A", ...}]
        on_progress=None,       # 可选回调，用于 WebSocket 实时推送进度
    ) -> list[dict]:
        """
        并发转写所有语音段（Pass 1 + Pass 2 边界修正）。

        从 transcribe_diarize.py 的 transcribe_parallel_async() 提取。
        """
        sem = asyncio.Semaphore(self.max_workers)

        async def _one(seg: dict, idx: int) -> dict:
            async with sem:
                text = await self.transcribe_segment(
                    wav_path, seg["start"], seg["end"]
                )
                result = {**seg, "text": text, "index": idx}
                if on_progress:
                    await on_progress(idx, len(segments), result)
                return result

        results = await asyncio.gather(*[
            _one(seg, i) for i, seg in enumerate(segments)
        ])
        return list(results)


def transcribe_segment(wav_path: str, start: float, end: float) -> str:
    """同步便捷函数（内部用 asyncio.run）"""
    svc = TranscriptionService()
    return asyncio.run(svc.transcribe_segment(wav_path, start, end))
