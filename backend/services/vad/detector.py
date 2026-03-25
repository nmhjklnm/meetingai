"""
VAD — FunASR FSMN-VAD（ModelScope）
=====================================
模型：iic/speech_fsmn_vad_zh-cn-16k-common-pytorch
缓存：由 MODELSCOPE_CACHE 环境变量指定目录（挂载为 Docker volume），仅下载一次。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

_MODEL_ID = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
_REVISION = "v2.0.4"

_model = None


def _get_model():
    global _model
    if _model is None:
        from funasr import AutoModel
        logger.info("加载 FSMN-VAD 模型（首次运行自动从 ModelScope 下载）...")
        _model = AutoModel(
            model=_MODEL_ID,
            model_revision=_REVISION,
            disable_update=True,
        )
        logger.info("FSMN-VAD 加载完成")
    return _model


@dataclass
class SpeechSegment:
    start: float  # 秒
    end: float    # 秒


class VADDetector:
    """
    FunASR FSMN-VAD 检测器。

    参数
    ----
    min_speech_ms : 过滤掉短于此时长的语音段（毫秒）
    """

    def __init__(self, min_speech_ms: int = 200):
        self.min_speech_ms = min_speech_ms

    def detect(self, wav_path: str | Path) -> List[SpeechSegment]:
        """检测 WAV 文件中的语音段，返回按时间排序的 SpeechSegment 列表"""
        model = _get_model()
        res = model.generate(
            input=str(wav_path),
            cache={},
            disable_pbar=True,
        )
        # 返回格式：[{'key': '...', 'value': [[start_ms, end_ms], ...]}]
        segments_ms: list = res[0].get("value", []) if res else []

        return [
            SpeechSegment(start=s / 1000.0, end=e / 1000.0)
            for s, e in segments_ms
            if (e - s) >= self.min_speech_ms
        ]


def detect_speech_segments(
    wav_path: str | Path, min_speech_ms: int = 200
) -> List[SpeechSegment]:
    return VADDetector(min_speech_ms).detect(wav_path)
