"""
说话人分离 Pipeline — CAM++（ModelScope）
==========================================
说话人嵌入：iic/speech_campplus_sv_zh-cn_16k-common（192 维，L2-normalized）
聚类：      KMeans（余弦空间）+ 轮廓系数自动检测说话人数 + 时序平滑
缓存：      MODELSCOPE_CACHE 环境变量指定目录（Docker volume），仅下载一次。
"""
from __future__ import annotations

import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

_CAMPPLUS_MODEL_ID = "iic/speech_campplus_sv_zh-cn_16k-common"
_CAMPPLUS_REVISION = "v2.0.2"

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from modelscope.pipelines import pipeline as ms_pipeline
        from modelscope.utils.constant import Tasks
        logger.info("加载 CAM++ 说话人嵌入模型（首次运行自动从 ModelScope 下载）...")
        _pipeline = ms_pipeline(
            task=Tasks.speaker_verification,
            model=_CAMPPLUS_MODEL_ID,
            model_revision=_CAMPPLUS_REVISION,
            device="cpu",
        )
        logger.info("CAM++ 加载完成")
    return _pipeline


@dataclass
class DiarizedSegment:
    start: float
    end: float
    speaker_id: str   # "Speaker A" / "Speaker B" / ...


# ── 音频加载（只读一次） ───────────────────────────────────────────────────────

def _load_wav(wav_path: str | Path) -> tuple[np.ndarray, int]:
    """
    将 WAV 文件全部读入内存，返回 (float32 归一化数组, 采样率)。
    调用方只执行一次，避免在每个片段里重复读取整个文件。
    """
    import wave
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sr


# ── 嵌入提取 ──────────────────────────────────────────────────────────────────

def _embed_segment_from_array(
    samples: np.ndarray, sr: int, start: float, end: float
) -> np.ndarray:
    """
    从已加载到内存的 numpy 数组中切出片段，写入临时文件后送入 CAM++ 推理。
    每次只写当前段（几秒），而不是整个文件，I/O 量从 GB 级降到 KB 级。
    """
    import soundfile as sf

    s, e = int(start * sr), int(end * sr)
    chunk = samples[s:e]
    if len(chunk) == 0:
        return np.zeros(192)

    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        sf.write(tmp, chunk, sr, subtype="PCM_16")
        pipe = _get_pipeline()
        # pipeline 期望一对音频做比较；output_emb=True 只取嵌入
        result = pipe([tmp, tmp], output_emb=True)
        emb = np.array(result["embs"][0], dtype=np.float32)
        norm = np.linalg.norm(emb)
        return emb / norm if norm > 0 else emb
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ── 聚类 & 平滑 ───────────────────────────────────────────────────────────────

def _auto_detect_speakers(embs: np.ndarray, min_spk: int, max_spk: int) -> int:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    n = len(embs)
    if n <= 1:
        return 1
    max_spk = min(max_spk, n - 1) if n > 2 else 1
    if max_spk <= min_spk:
        return min_spk

    best_k, best_score = min_spk, -1.0
    for k in range(min_spk, max_spk + 1):
        labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(embs)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(embs, labels, metric="cosine")
        if score > best_score:
            best_score, best_k = score, k
    return best_k


def _assign_speakers(embs: np.ndarray, n_cls: int) -> list[int]:
    from sklearn.cluster import KMeans
    return KMeans(n_clusters=n_cls, n_init=20, random_state=42).fit_predict(embs).tolist()


def _smooth_labels(
    labels: list[int], segs: list[tuple[float, float]], window: float = 8.0
) -> list[int]:
    from collections import Counter
    result = list(labels)
    for i, (s, e) in enumerate(segs):
        center = (s + e) / 2
        neighbors = [
            labels[j] for j, (ns, ne) in enumerate(segs)
            if abs((ns + ne) / 2 - center) < window and j != i
        ]
        if neighbors:
            majority = Counter(neighbors).most_common(1)[0][0]
            if neighbors.count(majority) >= len(neighbors) * 0.7:
                result[i] = majority
    return result


# ── 主 Pipeline ───────────────────────────────────────────────────────────────

class DiarizationPipeline:
    """
    说话人分离：CAM++ 嵌入 → KMeans 聚类 → 时序平滑 → 合并相邻段
    """

    def diarize(
        self,
        wav_path: str | Path,
        segs: list[tuple[float, float]],
        num_speakers: Optional[int] = None,
        min_speakers: int = 1,
        max_speakers: int = 8,
    ) -> List[DiarizedSegment]:
        """
        Args:
            wav_path     : 16kHz 单声道 WAV 文件路径
            segs         : [(start_sec, end_sec), ...]，由 VADDetector 输出
            num_speakers : 说话人数（None = 自动检测）
            min/max_speakers: 自动检测范围
        """
        logger.info("加载音频到内存...")
        samples, sr = _load_wav(wav_path)   # 只读一次，后续所有段共享

        # 限制 PyTorch 每次推理只用 1 个核，让多线程真正跑在不同核上
        try:
            import torch
            torch.set_num_threads(1)
        except Exception:
            pass

        n_workers = min(os.cpu_count() or 4, 8)
        logger.info("提取说话人嵌入（%d 段，%d 线程并行）...", len(segs), n_workers)

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            embeddings = list(pool.map(
                lambda se: _embed_segment_from_array(samples, sr, se[0], se[1]),
                segs,
            ))

        del samples  # 释放内存
        embs = np.array(embeddings)

        if num_speakers and num_speakers > 0:
            n_cls = min(num_speakers, len(segs))
        else:
            n_cls = _auto_detect_speakers(embs, min_speakers, max_speakers)
        n_cls = max(1, min(n_cls, len(segs)))
        logger.info("说话人数：%d", n_cls)

        labels_raw = _assign_speakers(embs, n_cls) if n_cls > 1 else [0] * len(segs)
        labels = _smooth_labels(labels_raw, segs)
        speaker_names = [f"Speaker {chr(65 + i)}" for i in range(n_cls)]

        return [
            DiarizedSegment(
                start=round(s, 3),
                end=round(e, 3),
                speaker_id=speaker_names[labels[i]],
            )
            for i, (s, e) in enumerate(segs)
        ]

    def merge_consecutive(
        self, segments: List[DiarizedSegment], gap_threshold: float = 1.5
    ) -> List[DiarizedSegment]:
        """合并相邻同说话人段"""
        merged: list[DiarizedSegment] = []
        for seg in segments:
            if (
                merged
                and merged[-1].speaker_id == seg.speaker_id
                and seg.start - merged[-1].end < gap_threshold
            ):
                merged[-1].end = seg.end
            else:
                merged.append(DiarizedSegment(seg.start, seg.end, seg.speaker_id))
        return merged
