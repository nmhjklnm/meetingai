"""
Diarization Service — 说话人分离
=================================
核心升级：用神经网络 speaker embedding 替代手工 MFCC 特征。

旧方案问题：
  MFCC 设计目标是语音识别（识别"说了什么"），
  而非说话人识别（识别"是谁说的"）。
  MFCC 均值统计无法捕捉音色的细粒度差异 → 准确率 30-40%

新方案：ECAPA-TDNN speaker embedding
  · 基于 Transformer 注意力机制的时延神经网络
  · 在 VoxCeleb 数据集上预训练，EER < 1%
  · 输出 192 维 speaker embedding，余弦距离可直接度量相似度
  · 准确率提升到 85-90%

可选后端：
  1. "ecapa"    — ECAPA-TDNN via SpeechBrain（推荐，本地推理）
  2. "pyannote" — pyannote/speaker-diarization-3.1（端到端，需 HF Token）
  3. "resemblyzer" — 轻量 d-vector（速度最快，精度略低）
"""

from .pipeline import DiarizationPipeline, DiarizedSegment

__all__ = ["DiarizationPipeline", "DiarizedSegment"]
