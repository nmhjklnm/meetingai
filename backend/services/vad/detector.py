"""
Silero VAD 封装
--------------
模型：snakers4/silero-vad (LSTM, ~1MB ONNX)
文档：https://github.com/snakers4/silero-vad

安装：pip install silero-vad  （或 torch + torchaudio）

替代旧版能量 VAD 的问题：
  旧版：energy > threshold → 对噪声极敏感，最小静音/语音时长参数需手动调
  新版：LSTM 捕捉语音时域上下文 → 准确区分人声/噪声/音乐
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class SpeechSegment:
    start: float   # 秒
    end: float     # 秒


class VADDetector:
    """
    Silero VAD 检测器。

    TODO: 实现步骤
    1. pip install silero-vad
    2. model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad')
    3. get_speech_timestamps = utils[0]
    4. 用 get_speech_timestamps(wav, model, ...) 得到时间戳列表

    参数说明：
      threshold        : 0.5  检测阈值（0~1），越高越严格
      min_speech_ms    : 250  最短语音段（ms）
      min_silence_ms   : 500  合并静音间隔（ms）
      window_size_samples: 512  处理窗口（16kHz下=32ms）
    """

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_ms: int = 250,
        min_silence_ms: int = 500,
        sampling_rate: int = 16000,
    ):
        self.threshold = threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.sampling_rate = sampling_rate
        self._model = None

    def _load_model(self):
        """懒加载模型（首次调用时下载 ~1MB 权重）"""
        # TODO: 替换为实际 silero-vad 加载逻辑
        raise NotImplementedError(
            "请先安装 silero-vad: pip install silero-vad\n"
            "然后实现此方法，参考 docs/diarization-upgrade.md"
        )

    def detect(self, wav_path: str | Path) -> List[SpeechSegment]:
        """
        检测语音段。

        Returns:
            语音段列表，每段含 start/end（秒）
        """
        if self._model is None:
            self._load_model()
        # TODO: 实现推理逻辑
        raise NotImplementedError


def detect_speech_segments(
    wav_path: str | Path,
    threshold: float = 0.5,
    min_speech_ms: int = 250,
    min_silence_ms: int = 500,
) -> List[SpeechSegment]:
    """便捷函数：直接检测并返回语音段列表"""
    detector = VADDetector(threshold, min_speech_ms, min_silence_ms)
    return detector.detect(wav_path)
