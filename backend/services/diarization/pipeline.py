"""
说话人分离 Pipeline
-------------------
完整流程：
  WAV → VAD → ECAPA-TDNN Embedding → AHC聚类 → 自动检测说话人数 → 标签

替代当前手工 MFCC 方案的核心改进：

旧方案嵌入（249维手工统计）：
  MFCC(20) + Δ + ΔΔ → mean/std/q25/q75 = 240维
  + 谱质心/ZCR = 6维 + F0统计 = 3维
  问题：统计特征损失了时序结构，对相似音色的说话人无能为力

新方案嵌入（192维神经网络）：
  ECAPA-TDNN 在数千小时多说话人数据上预训练
  输入：任意长度语音段
  输出：192维 L2-normalized embedding（说话人身份 fingerprint）
  同一人：余弦相似度 > 0.85
  不同人：余弦相似度 < 0.60

聚类改进：
  旧：KMeans（欧氏距离，对高维数据敏感）
  新：AHC + 余弦距离 + 自动阈值（无需指定说话人数量）
      → 当相邻合并的余弦距离 > 0.4 时停止合并
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import os


@dataclass
class DiarizedSegment:
    start: float          # 秒
    end: float            # 秒
    speaker_id: str       # "SPEAKER_00", "SPEAKER_01", ...
    embedding: Optional[list] = field(default=None, repr=False)


class DiarizationPipeline:
    """
    说话人分离 Pipeline。

    支持两种后端：
    1. "ecapa" (默认)
       - 依赖：pip install speechbrain
       - 模型：speechbrain/spkrec-ecapa-voxceleb
       - 本地推理，无需 Token
       - 首次运行自动下载 ~80MB 模型

    2. "pyannote"
       - 依赖：pip install pyannote.audio
       - 模型：pyannote/speaker-diarization-3.1
       - 需要 HuggingFace Token（HF_TOKEN 环境变量）
       - 端到端，内置 VAD + 分割 + 聚类
       - 最准，但模型更大（~200MB）

    TODO 实现计划（见 docs/diarization-upgrade.md）：
    Phase 1: 集成 Resemblyzer（最快验证）
    Phase 2: 集成 ECAPA-TDNN（生产推荐）
    Phase 3: 可选 pyannote 后端
    """

    def __init__(
        self,
        backend: str = "ecapa",
        hf_token: Optional[str] = None,
        device: str = "cpu",
    ):
        self.backend = backend
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.device = device
        self._model = None

    def _load_ecapa(self):
        """加载 ECAPA-TDNN speaker encoder"""
        # TODO:
        # from speechbrain.pretrained import EncoderClassifier
        # self._model = EncoderClassifier.from_hparams(
        #     source="speechbrain/spkrec-ecapa-voxceleb",
        #     run_opts={"device": self.device}
        # )
        raise NotImplementedError(
            "请安装 speechbrain: pip install speechbrain\n"
            "参考 docs/diarization-upgrade.md"
        )

    def _load_pyannote(self):
        """加载 pyannote 端到端 pipeline"""
        # TODO:
        # from pyannote.audio import Pipeline
        # self._model = Pipeline.from_pretrained(
        #     "pyannote/speaker-diarization-3.1",
        #     use_auth_token=self.hf_token
        # )
        raise NotImplementedError(
            "请安装 pyannote.audio: pip install pyannote.audio\n"
            "并设置 HF_TOKEN 环境变量\n"
            "参考 docs/diarization-upgrade.md"
        )

    def embed(self, wav_segment: "np.ndarray", sr: int) -> "np.ndarray":
        """
        将音频段编码为 192 维 speaker embedding。

        替代旧版 _embed_chunk()，使用神经网络特征而非手工统计。
        """
        if self._model is None:
            if self.backend == "ecapa":
                self._load_ecapa()
            elif self.backend == "pyannote":
                self._load_pyannote()
        raise NotImplementedError

    def diarize(
        self,
        wav_path: str | Path,
        num_speakers: Optional[int] = None,   # None = 自动检测
        min_speakers: int = 1,
        max_speakers: int = 10,
    ) -> List[DiarizedSegment]:
        """
        对完整音频文件做说话人分离。

        Args:
            wav_path: 16kHz 单声道 WAV 文件
            num_speakers: 说话人数量，None 时自动检测
            min_speakers: 自动检测时的最小值
            max_speakers: 自动检测时的最大值

        Returns:
            DiarizedSegment 列表，含 start/end/speaker_id
        """
        raise NotImplementedError

    def auto_detect_num_speakers(
        self,
        embeddings: "np.ndarray",
        min_k: int = 1,
        max_k: int = 10,
        threshold: float = 0.4,  # 余弦距离停止阈值
    ) -> int:
        """
        基于 AHC 树状图自动检测说话人数量。

        改进旧版"惩罚轮廓系数"方案：
        直接用 AHC 树状图的合并距离变化率（elbow detection）
        → 当下一次合并的余弦距离 > threshold 时停止

        这比轮廓系数更直观，且不需要多次运行 KMeans。
        """
        raise NotImplementedError


def diarize(
    wav_path: str | Path,
    backend: str = "ecapa",
    num_speakers: Optional[int] = None,
) -> List[DiarizedSegment]:
    """便捷函数"""
    pipeline = DiarizationPipeline(backend=backend)
    return pipeline.diarize(wav_path, num_speakers=num_speakers)
