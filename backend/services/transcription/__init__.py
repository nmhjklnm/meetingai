"""
Transcription Service — 语音转文字
====================================
当前方案：GPT-4o-transcribe（效果已很好，保留）

未来可替换为：
  · Whisper Large V3（本地，无需 API Key）
  · faster-whisper（CTranslate2 优化版，本地，速度 4x）
  · Azure Cognitive Services Speech
  · Google Cloud Speech-to-Text v2
"""

from .transcriber import TranscriptionService, transcribe_segment

__all__ = ["TranscriptionService", "transcribe_segment"]
