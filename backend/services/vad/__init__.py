"""
VAD Service — Voice Activity Detection
=======================================
替代原有能量阈值 VAD，使用 Silero VAD（基于 LSTM，ONNX 推理）。

改进点：
  - 误检率降低 ~80%（能区分噪声和语音）
  - 支持流式处理
  - 延迟 < 10ms/帧

用法：
  from backend.services.vad import detect_speech_segments
  segments = detect_speech_segments("audio.wav")
  # [{"start": 0.5, "end": 3.2}, {"start": 4.1, "end": 8.7}, ...]
"""

from .detector import detect_speech_segments, VADDetector

__all__ = ["detect_speech_segments", "VADDetector"]
