"""
转写服务 — 基于 OpenAI-compatible API（GPT-4o-transcribe）
----------------------------------------------------------
  · AsyncOpenAI 并发调用（Semaphore 控制并发数）
  · language="zh" 锁定语言，防止乱码输出其他语种
  · prompt 注入领域术语，提升关键词识别准确率
  · 后处理：清除残留的非中英文字符（日/韩/格鲁吉亚语等乱码）
  · 指数退避自动重试（3次）
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

# ── 默认领域 prompt ────────────────────────────────────────────────────────────
# Whisper 用 prompt 做解码偏置：出现在 prompt 里的词会被优先识别。
# 用户可在上传时传入自定义 prompt 覆盖此默认值。
DEFAULT_PROMPT = (
    "以下是一段中文会议录音，讨论AI Agent平台产品设计与开发。"
    "技术术语：Claude、cursor、Cursor、VPS、session ID、API key、"
    "sandbox（沙盒）、agent、member、space、conversation、workspace、"
    "分身、工作流、FastAPI、Python、MCP、LLM、token、"
    "前端、后端、SDK、Docker、Redis、PostgreSQL。"
    "说话人使用中英文混合表达，英文专有名词保持原文不翻译。"
)

# 合法字符范围：中文 + 纯 ASCII（英文/数字/标点）+ 中文标点
# 不包含 Latin Extended（ë ž ü 等欧洲字符），避免误识别为阿尔巴尼亚/捷克语等
_ALIEN_LANG_RE = re.compile(
    r'[^\u4e00-\u9fff'       # 中文 CJK
    r'\u0020-\u007e'         # 纯 ASCII（英文/数字/基本标点）
    r'\uff00-\uffef'         # 全角字符
    r'\u3000-\u303f'         # CJK 标点
    r'，。！？、；：""''（）【】…—\n\r\t]+',
)


def _clean_transcript(text: str) -> str:
    """
    将乱码语种（格鲁吉亚语、韩语、阿尔巴尼亚语等）替换为 [unclear]。
    保留中文、英文（纯 ASCII）、数字和常用标点。

    两步处理：
    1. 字符级：把非法字符集替换为 [unclear]
    2. 词级：把"含有非法字符的整个单词"也整体替换，避免留下 un[unclear]xxx 残骸
    """
    if not text:
        return text
    # 步骤 1：找出含非法字符的整个 token（连续非空白字符序列），整体替换
    def _replace_token(m: re.Match) -> str:
        token = m.group(0)
        if _ALIEN_LANG_RE.search(token):
            return "[unclear]"
        return token
    # 匹配一个连续非空白 token
    cleaned = re.sub(r'\S+', _replace_token, text)
    # 步骤 2：合并多个连续 [unclear]
    cleaned = re.sub(r'(\[unclear\]\s*){2,}', '[unclear] ', cleaned)
    return cleaned.strip()


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
        language: str = "zh",
        prompt: Optional[str] = None,
    ):
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.language = language
        self.prompt = prompt if prompt is not None else DEFAULT_PROMPT

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
        _wav_cache: dict | None = None,
    ) -> str:
        """
        转写单个语音段，从内存缓存切片后调用 API。

        _wav_cache: 可选的共享缓存字典 {"samples": ndarray, "sr": int}，
                    由 transcribe_batch 统一传入以避免重复读盘。
        """
        import io
        import struct
        import wave as wavemod

        client = self._get_client()

        # ── 获取 float32 音频数组 ──────────────────────────────────────────────
        if _wav_cache is not None and "samples" in _wav_cache:
            samples = _wav_cache["samples"]
            sr = _wav_cache["sr"]
        else:
            with wavemod.open(str(wav_path), "rb") as wf:
                sr = wf.getframerate()
                raw = wf.readframes(wf.getnframes())
            samples = __import__("numpy").frombuffer(raw, dtype="int16").astype("float32") / 32768.0

        s_idx = int(start * sr)
        e_idx = int(end * sr)
        chunk_f32 = samples[s_idx:e_idx]
        if len(chunk_f32) == 0:
            return ""

        # ── 将 float32 → PCM16 WAV bytes（内存，无磁盘 I/O） ─────────────────
        chunk_i16 = (chunk_f32 * 32767).clip(-32768, 32767).astype("int16")
        buf = io.BytesIO()
        with wavemod.open(buf, "wb") as wout:
            wout.setnchannels(1)
            wout.setsampwidth(2)
            wout.setframerate(sr)
            wout.writeframes(chunk_i16.tobytes())
        wav_bytes = buf.getvalue()

        # ── API 调用 + 重试 ────────────────────────────────────────────────────
        # 优先使用调用方传入的 prompt，否则用实例默认的领域 prompt
        effective_prompt = prompt if prompt else self.prompt
        for attempt in range(retries):
            if attempt > 0:
                await asyncio.sleep(2 ** attempt)
            try:
                audio_file = ("audio.wav", io.BytesIO(wav_bytes), "audio/wav")
                resp = await client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    response_format="text",
                    language=self.language,
                    extra_body={"prompt": effective_prompt} if effective_prompt else {},
                )
                raw = (getattr(resp, "text", None) or str(resp)).strip()
                return _clean_transcript(raw)   # 后处理：清除乱码语种
            except Exception as exc:
                if attempt == retries - 1:
                    return f"[ERROR: {exc}]"
        return ""

    async def transcribe_batch(
        self,
        wav_path: str | Path,
        segments: list[dict],   # [{"start": 0.5, "end": 3.2, "speaker": "A", ...}]
        on_progress=None,
    ) -> list[dict]:
        """
        并发转写所有语音段。
        音频文件只读一次加载到内存，所有并发任务共享，无重复磁盘 I/O。
        """
        import numpy as np
        import wave as wavemod

        # 音频只读一次
        with wavemod.open(str(wav_path), "rb") as wf:
            sr = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
        wav_cache = {
            "samples": np.frombuffer(raw, dtype="int16").astype("float32") / 32768.0,
            "sr": sr,
        }

        sem = asyncio.Semaphore(self.max_workers)

        async def _one(seg: dict, idx: int) -> dict:
            async with sem:
                text = await self.transcribe_segment(
                    wav_path, seg["start"], seg["end"],
                    _wav_cache=wav_cache,
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
