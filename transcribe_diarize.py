"""
语音转写 + 说话人识别  ·  v3
────────────────────────────────────────────────────────────
本版本修复的问题：
  [标点] 段尾缺少句号、段间文本被截断  → 上下文 prompt 传递
  [标点] 并发模式无法传递上下文         → 二阶边界修正 pass
  [说话人] 短片段聚类不稳定             → delta-MFCC + 时序平滑
  [输出] 同一说话人相邻段碎片化         → 后处理合并 + 补句末标点

用法：
  uv run python transcribe_diarize.py <音频>
  uv run python transcribe_diarize.py <音频> 3 --parallel --workers 8
  uv run python transcribe_diarize.py <音频> --no-merge   # 保留原始分段
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import numpy as np
from numpy.lib.stride_tricks import as_strided
from scipy.fft import dct as scipy_dct
from tqdm import tqdm
from tqdm.asyncio import tqdm as atqdm

# ── 配置 ──────────────────────────────────────────────────────────────────────
BASE_URL            = os.getenv("OPENAI_BASE_URL", "https://yunwu.ai/v1")
API_KEY             = os.getenv("OPENAI_API_KEY", "")
MODEL               = os.getenv("TRANSCRIPTION_MODEL", "gpt-4o-transcribe")
MAX_WORKERS_DEFAULT = 5

# 句末标点集合（用于判断一句是否完整）
SENTENCE_END   = set("。！？…")
# 连接词：前段以这些结尾，说明句子跨段
CONTINUATIVES  = ("所以", "因为", "但是", "然后", "而且", "而", "就",
                  "才", "也", "又", "还", "对，", "嗯，")
# ─────────────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# §1  音频 I/O
# ══════════════════════════════════════════════════════════════════════════════

def to_wav(src: str, dst: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", src,
         "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", dst],
        check=True, capture_output=True,
    )


def concat_parts_to_wav(audio_files: list[str], dst: str) -> list[float]:
    """
    把多个音频文件拼接成一个 WAV。
    返回每个 part 在合并后音频中的起始秒数列表（第一个始终为 0）。
    """
    import shlex
    # 先获取各文件时长
    offsets: list[float] = []
    acc = 0.0
    for f in audio_files:
        offsets.append(acc)
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", f],
            stderr=subprocess.DEVNULL,
        )
        acc += float(out.strip())

    # 写 filelist.txt（concat demuxer 需要绝对路径）
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as flist:
        flist_path = flist.name
        for f in audio_files:
            flist.write(f"file '{Path(f).resolve()}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", flist_path,
         "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", dst],
        check=True, capture_output=True,
    )
    os.unlink(flist_path)
    return offsets


def load_pcm(wav_path: str) -> tuple[np.ndarray, int]:
    with wave.open(wav_path, "rb") as wf:
        sr  = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, sr


def cut_segment(wav_path: str, start: float, end: float) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path,
         "-ss", str(start), "-to", str(end),
         "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", tmp],
        check=True, capture_output=True,
    )
    return tmp


# ══════════════════════════════════════════════════════════════════════════════
# §2  VAD — 向量化，更大合并窗口减少句内碎片
# ══════════════════════════════════════════════════════════════════════════════

def vad_segments(
    samples: np.ndarray, sr: int,
    frame_ms: int = 30,
    thresh: float = 0.015,
    min_speech_ms: int = 1500,   # 提高到 1.5s，避免短片段噪声
    pad_ms: int = 250,
    min_silence_ms: int = 600,   # 600ms 内的静音视为同一句，不分段
) -> list[tuple[float, float]]:
    frame_len  = int(sr * frame_ms / 1000)
    pad_f      = int(pad_ms / frame_ms)
    min_sil_f  = int(min_silence_ms / frame_ms)

    n_frames = (len(samples) - frame_len) // frame_len
    frames   = samples[: n_frames * frame_len].reshape(n_frames, frame_len)
    energies = np.sqrt(np.mean(frames ** 2, axis=1))
    is_speech = energies > thresh

    raw: list[list[int]] = []
    in_seg = False
    for i, s in enumerate(is_speech):
        if s and not in_seg:
            in_seg = True
            start  = max(0, i - pad_f)
        elif not s and in_seg:
            raw.append([start, min(n_frames - 1, i + pad_f)])
            in_seg = False
    if in_seg:
        raw.append([start, n_frames - 1])

    merged: list[list[int]] = []
    for seg in raw:
        if merged and seg[0] - merged[-1][1] < min_sil_f:
            merged[-1][1] = seg[1]
        else:
            merged.append(seg)

    return [
        (s * frame_ms / 1000, e * frame_ms / 1000)
        for s, e in merged
        if (e - s) * frame_ms >= min_speech_ms
    ]


# ══════════════════════════════════════════════════════════════════════════════
# §3  MFCC（全向量化）+ delta 特征
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=16)
def _mel_filterbank(sr: int, n_fft: int, n_mels: int = 26,
                    fmin: int = 80, fmax: int = 7600) -> np.ndarray:
    hz2mel = lambda h: 2595 * np.log10(1 + h / 700)
    mel2hz = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = np.floor(
        (n_fft + 1) * mel2hz(
            np.linspace(hz2mel(fmin), hz2mel(fmax), n_mels + 2)
        ) / sr
    ).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        lo, cen, hi = pts[m - 1], pts[m], pts[m + 1]
        if cen > lo:
            fb[m - 1, lo:cen] = (np.arange(lo, cen) - lo) / (cen - lo)
        if hi > cen:
            fb[m - 1, cen:hi] = (hi - np.arange(cen, hi)) / (hi - cen)
    return fb


def extract_mfcc(samples: np.ndarray, sr: int,
                 n_mfcc: int = 20, frame_ms: int = 25, hop_ms: int = 10) -> np.ndarray:
    s = np.empty_like(samples)
    s[0] = samples[0]
    s[1:] = samples[1:] - 0.97 * samples[:-1]

    flen  = int(sr * frame_ms / 1000)
    fhop  = int(sr * hop_ms   / 1000)
    n_fft = 1 << (flen - 1).bit_length()
    n_frames = max(1, (len(s) - flen) // fhop)
    if len(s) < flen:
        return np.zeros((1, n_mfcc))

    frames = as_strided(
        s,
        shape=(n_frames, flen),
        strides=(s.strides[0] * fhop, s.strides[0]),
    ).copy() * np.hamming(flen)

    spec    = np.abs(np.fft.rfft(frames, n=n_fft, axis=1)) ** 2
    fb      = _mel_filterbank(sr, n_fft)
    log_mel = np.log(np.maximum(spec @ fb.T, 1e-8))
    return scipy_dct(log_mel, type=2, n=n_mfcc, axis=1, norm="ortho")


def _pitch_stats(samples: np.ndarray, sr: int,
                  frame_ms: int = 25, hop_ms: int = 10) -> np.ndarray:
    """
    全向量化 F0 统计（批量 FFT 自相关，无 Python for 循环）。
    返回 [voiced_F0_mean, voiced_F0_std, voiced_fraction] 3 维。
    """
    flen    = int(sr * frame_ms / 1000)
    fhop    = int(sr * hop_ms   / 1000)
    min_lag = max(1, sr // 500)   # ≤500 Hz
    max_lag = min(sr // 60, flen - 1)   # ≥60 Hz

    if len(samples) < flen or max_lag <= min_lag:
        return np.zeros(3)

    n_frames = max(1, (len(samples) - flen) // fhop)
    frames = as_strided(
        samples,
        shape=(n_frames, flen),
        strides=(samples.strides[0] * fhop, samples.strides[0]),
    ).copy()
    frames -= frames.mean(axis=1, keepdims=True)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    voiced = rms > 0.005
    if not voiced.any():
        return np.zeros(3)

    vf = frames[voiced]                                          # (V, flen)
    N  = 1 << (2 * flen - 1).bit_length()
    F  = np.fft.rfft(vf, n=N, axis=1)
    acf = np.fft.irfft(F * np.conj(F), n=N, axis=1)[:, :flen]  # (V, flen)
    a0  = acf[:, 0:1]
    a0_safe = np.where(a0 > 0, a0, 1.0)
    acf_n = acf / a0_safe                                        # 归一化

    search  = acf_n[:, min_lag:max_lag]                          # (V, lag_range)
    rel_idx = np.argmax(search, axis=1)                          # (V,)
    lag_idx = rel_idx + min_lag
    peak_v  = acf_n[np.arange(len(vf)), lag_idx]

    f0_mask = (peak_v > 0.30) & (a0[:, 0] > 0)
    if f0_mask.sum() < 3:
        return np.zeros(3)

    f0_vals = sr / lag_idx[f0_mask].astype(float)
    return np.array([f0_vals.mean(), f0_vals.std(),
                     float(f0_mask.sum()) / n_frames])


def _spectral_stats(samples: np.ndarray, sr: int,
                    frame_ms: int = 25, hop_ms: int = 10) -> np.ndarray:
    """谱质心 + 谱滚降点 + ZCR 的均值/标准差，共 6 维。"""
    flen   = int(sr * frame_ms / 1000)
    fhop   = int(sr * hop_ms   / 1000)
    n_fft  = 1 << (flen - 1).bit_length()
    n_frames = max(1, (len(samples) - flen) // fhop)
    if len(samples) < flen:
        return np.zeros(6)

    frames = as_strided(
        samples,
        shape=(n_frames, flen),
        strides=(samples.strides[0] * fhop, samples.strides[0]),
    ).copy() * np.hamming(flen)

    spec  = np.abs(np.fft.rfft(frames, n=n_fft, axis=1))  # (T, bins)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)              # (bins,)
    power = spec ** 2
    p_sum = power.sum(axis=1, keepdims=True) + 1e-8

    # 谱质心
    centroid = (power @ freqs) / p_sum[:, 0]

    # 谱滚降（85% 能量）
    cumsum  = np.cumsum(power, axis=1)
    thresh  = 0.85 * p_sum
    rolloff = freqs[np.argmax(cumsum >= thresh, axis=1)]

    # ZCR（每帧）
    orig_frames = as_strided(
        samples,
        shape=(n_frames, flen),
        strides=(samples.strides[0] * fhop, samples.strides[0]),
    )
    zcr = (np.diff(np.sign(orig_frames), axis=1) != 0).mean(axis=1).astype(float)

    return np.array([
        centroid.mean(), centroid.std(),
        rolloff.mean(),  rolloff.std(),
        zcr.mean(),      zcr.std(),
    ])


def _embed_chunk(args: tuple[np.ndarray, int]) -> np.ndarray:
    """
    增强说话人嵌入（~180 维，L2 归一化）：
      · MFCC(20) + Δ(20) + ΔΔ(20) × {mean, std, q25, q75} = 240 维
      · 谱质心/滚降/ZCR                                      =   6 维
      · F0 统计（均值/标准差/有声率）                        =   3 维
    最终 L2 归一化 → 后续余弦距离聚类效果更好
    """
    chunk, sr = args
    if len(chunk) < 320:
        return np.zeros(249)

    mfcc   = extract_mfcc(chunk, sr, n_mfcc=20)              # (T, 20)
    delta  = np.diff(mfcc, axis=0, prepend=mfcc[:1])         # (T, 20)
    delta2 = np.diff(delta, axis=0, prepend=delta[:1])       # (T, 20)
    feat   = np.concatenate([mfcc, delta, delta2], axis=1)   # (T, 60)

    q25, q75 = np.percentile(feat, [25, 75], axis=0)
    mfcc_part = np.concatenate([
        feat.mean(0), feat.std(0), q25, q75,                  # 240 维
    ])
    spec_part  = _spectral_stats(chunk, sr)                   #   6 维
    pitch_part = _pitch_stats(chunk, sr)                      #   3 维

    return np.concatenate([mfcc_part, spec_part, pitch_part])  # 249 维，不做全局 L2


def build_embeddings_parallel(
    samples: np.ndarray, sr: int, segs: list[tuple[float, float]]
) -> np.ndarray:
    chunks    = [(samples[int(s * sr): int(e * sr)], sr) for s, e in segs]
    n_workers = min(os.cpu_count() or 4, len(segs))
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        embs = list(tqdm(
            pool.map(_embed_chunk, chunks),
            total=len(chunks), desc="  嵌入", leave=False,
        ))
    return np.array(embs)


# ══════════════════════════════════════════════════════════════════════════════
# §4  说话人聚类 + 时序平滑
# ══════════════════════════════════════════════════════════════════════════════

def assign_speakers(embeddings: np.ndarray, n_speakers: int) -> np.ndarray:
    """KMeans（标准化后欧氏距离）。"""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    if n_speakers == 1 or len(embeddings) <= n_speakers:
        return np.zeros(len(embeddings), dtype=int)

    X = StandardScaler().fit_transform(embeddings)
    return KMeans(
        n_clusters=n_speakers, n_init=30, max_iter=500, random_state=42
    ).fit_predict(X).astype(int)


def auto_detect_speakers(
    embeddings: np.ndarray,
    segs: list[tuple[float, float]],
    min_spk: int = 1,
    max_spk: int = 8,
) -> int:
    """
    无监督说话人数量检测。

    判断依据：惩罚轮廓系数
      silhouette_penalized(k) = silhouette(k) × min(1, min_dur_frac / 0.03)

    直觉：若某个 k 使某位说话人的总时长占比 < 3%（"幽灵说话人"），
    则对该 k 的轮廓分大幅降权 → k 自动收敛到有意义的说话人数量。
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score

    if len(embeddings) <= min_spk:
        return min_spk

    X = StandardScaler().fit_transform(embeddings)
    total_dur = sum(e - s for s, e in segs)

    best_k = min_spk
    best_score = -np.inf
    detail: list[str] = []

    for k in range(min_spk, min(max_spk + 1, len(embeddings))):
        km = KMeans(n_clusters=k, n_init=30, max_iter=500, random_state=42).fit(X)
        labels = km.labels_
        if len(set(labels)) < 2:
            continue

        sil = silhouette_score(X, labels)

        # 最小说话人时长占比（用于惩罚幽灵说话人）
        dur: dict[int, float] = {}
        for i, (s, e) in enumerate(segs):
            dur[labels[i]] = dur.get(labels[i], 0.0) + (e - s)
        min_frac = min(dur.values()) / total_dur

        # 惩罚系数：min_frac < 3% 时线性衰减
        penalty = min(1.0, min_frac / 0.03)
        penalized = sil * penalty

        detail.append(
            f"k={k}  sil={sil:.3f}  min_dur={min_frac*100:.1f}%  "
            f"penalty={penalty:.2f}  score={penalized:.3f}"
        )
        if penalized > best_score:
            best_score = penalized
            best_k = k

    for line in detail:
        print(f"    {line}" + ("  ← 选定" if line.startswith(f"k={best_k} ") else ""))

    return best_k


def smooth_speaker_labels(
    labels: list[int],
    segs: list[tuple[float, float]],
    short_thresh: float = 4.0,
    window: int = 2,
) -> list[int]:
    """
    多轮时序平滑：
    Pass 1 — 短段（< short_thresh 秒）若前后说话人相同则合并
    Pass 2 — 滑动投票窗口（±window 段），少数段服从多数
    """
    if len(labels) < 3:
        return labels

    # Pass 1：前后一致则合并短段
    smoothed = list(labels)
    for i in range(1, len(labels) - 1):
        dur = segs[i][1] - segs[i][0]
        if dur < short_thresh and smoothed[i - 1] == smoothed[i + 1]:
            smoothed[i] = smoothed[i - 1]

    # Pass 2：滑动投票（对孤立段再次平滑）
    result = list(smoothed)
    for i in range(len(smoothed)):
        lo = max(0, i - window)
        hi = min(len(smoothed), i + window + 1)
        nbrs = smoothed[lo:hi]
        # 仅对持续时间 < short_thresh 的段进行投票
        dur = segs[i][1] - segs[i][0]
        if dur < short_thresh:
            votes = {}
            for lbl in nbrs:
                votes[lbl] = votes.get(lbl, 0) + 1
            result[i] = max(votes, key=votes.get)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# §5  标点 / 上下文工具
# ══════════════════════════════════════════════════════════════════════════════

_BASE_PROMPT = "以下是一段中文商务对话录音的转写，请准确识别并添加标点符号。"


def _build_prompt(prev_text: str) -> str:
    """构造 API prompt：将上一段末尾作为上下文，帮助模型补全标点和连贯性"""
    if not prev_text:
        return _BASE_PROMPT
    tail = prev_text.strip()[-200:]
    return f"{_BASE_PROMPT}\n上文末尾：「…{tail}」"


def _is_incomplete(text: str) -> bool:
    """判断文本是否明显不完整（用于触发二阶修正）"""
    if not text:
        return True
    if text[-1] not in SENTENCE_END:
        return True
    if any(text.endswith(c) for c in CONTINUATIVES):
        return True
    return False


def _fix_punctuation(text: str) -> str:
    """后处理：补全缺失句末标点，清理重复标点"""
    text = text.strip()
    if not text:
        return text
    # 清理连续标点
    text = re.sub(r'([。！？，、；：])\1+', r'\1', text)
    # 末尾补句号（如果缺少）
    if text and text[-1] not in SENTENCE_END and text[-1] not in '，、；：':
        text += '。'
    return text


# ══════════════════════════════════════════════════════════════════════════════
# §6a  串行流式转写（实时打印 delta，携带上下文 prompt）
# ══════════════════════════════════════════════════════════════════════════════

def transcribe_sequential(
    wav_path: str,
    segs: list[tuple[float, float]],
    labels: list[int],
    speaker_names: list[str],
) -> list[dict]:
    from openai import OpenAI
    client  = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    results: list[dict] = []
    prev_text = ""

    print("─" * 64)
    for (start, end), label in zip(segs, labels):
        spk    = speaker_names[label]
        prompt = _build_prompt(prev_text)
        print(f"[{start:6.2f}s → {end:6.2f}s]  {spk}: ", end="", flush=True)

        tmp   = cut_segment(wav_path, start, end)
        final = ""
        try:
            with open(tmp, "rb") as af:
                stream = client.audio.transcriptions.create(
                    model=MODEL, file=af, response_format="text",
                    stream=True, extra_body={"prompt": prompt},
                )
                for event in stream:
                    etype = getattr(event, "type", "")
                    if etype == "transcript.text.delta":
                        d = getattr(event, "delta", "") or ""
                        print(d, end="", flush=True)
                    elif etype == "transcript.text.done":
                        final = getattr(event, "text", "") or ""
        finally:
            os.unlink(tmp)

        final = _fix_punctuation(final)
        print() if final else print("(静音)")
        prev_text = final
        results.append(_make_result(start, end, spk, final))

    print("─" * 64)
    return results


# ══════════════════════════════════════════════════════════════════════════════
# §6b  并发异步转写（两阶段：快速 pass1 + 边界修正 pass2）
# ══════════════════════════════════════════════════════════════════════════════

async def _transcribe_one(
    client, sem: asyncio.Semaphore,
    idx: int, wav_path: str,
    start: float, end: float,
    spk: str,
    prompt: str = _BASE_PROMPT,
    max_retries: int = 3,
) -> tuple[int, dict]:
    """切片 + 转写，自动重试（指数退避）"""
    loop = asyncio.get_running_loop()
    async with sem:
        last_err = ""
        for attempt in range(max_retries):
            if attempt > 0:
                await asyncio.sleep(2 ** attempt)   # 2s, 4s 退避
            tmp = await loop.run_in_executor(None, cut_segment, wav_path, start, end)
            try:
                with open(tmp, "rb") as af:
                    resp = await client.audio.transcriptions.create(
                        model=MODEL, file=af, response_format="text",
                        extra_body={"prompt": prompt},
                    )
                text = (getattr(resp, "text", None) or str(resp)).strip()
                return idx, _make_result(start, end, spk, text)
            except Exception as exc:
                last_err = str(exc)
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
    return idx, _make_result(start, end, spk, f"[ERROR: {last_err}]")


async def transcribe_parallel_async(
    wav_path: str,
    segs: list[tuple[float, float]],
    labels: list[int],
    speaker_names: list[str],
    max_workers: int = MAX_WORKERS_DEFAULT,
) -> list[dict]:
    from openai import AsyncOpenAI
    loop   = asyncio.get_event_loop()
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    sem    = asyncio.Semaphore(max_workers)

    # ── Pass 1：并行切片 + 并发转写 ──────────────────────────────────────────
    print(f"  [Pass 1] 并发转写 {len(segs)} 段（Semaphore={max_workers}，自动重试）...")
    tasks = [
        _transcribe_one(client, sem, i, wav_path,
                        segs[i][0], segs[i][1], speaker_names[labels[i]])
        for i in range(len(segs))
    ]
    pairs: list[tuple[int, dict]] = await atqdm.gather(*tasks, desc="  转写 P1")
    pairs.sort(key=lambda x: x[0])
    results = [r for _, r in pairs]

    # ── Pass 2：边界修正（对缺失句末标点或明显截断的段重新转写）─────────────
    needs_fix = [
        i for i, r in enumerate(results)
        if _is_incomplete(r["text"]) and not r["text"].startswith("[ERROR")
    ]
    if needs_fix:
        print(f"  [Pass 2] 修正 {len(needs_fix)} 个边界段（补上下文 prompt）...")
        fix_tasks = []
        for i in needs_fix:
            r      = results[i]
            prev   = results[i - 1]["text"] if i > 0 else ""
            prompt = _build_prompt(prev)
            fix_tasks.append(
                _transcribe_one(client, sem, i, wav_path,
                                r["start"], r["end"], r["speaker"], prompt)
            )
        fixed_pairs = await atqdm.gather(*fix_tasks, desc="  修正 P2")
        for fi, fr in fixed_pairs:
            results[fi] = fr

    # ── 后处理标点 ────────────────────────────────────────────────────────────
    for r in results:
        r["text"] = _fix_punctuation(r["text"])

    return results


# ══════════════════════════════════════════════════════════════════════════════
# §7  输出后处理
# ══════════════════════════════════════════════════════════════════════════════

def merge_consecutive_speakers(results: list[dict]) -> list[dict]:
    """
    合并相邻的同说话人段，消除 VAD 碎片化造成的人为断句。
    合并后 text 之间用空格连接（便于人工阅读）。
    """
    merged: list[dict] = []
    for r in results:
        if (merged
                and merged[-1]["speaker"] == r["speaker"]
                and r["start"] - merged[-1]["end"] < 1.5):
            # 合并：去掉上一段的假句末标点（如果是因截断补的），再接续文本
            prev_text = merged[-1]["text"].rstrip("。")
            merged[-1]["text"] = prev_text + r["text"]
            merged[-1]["end"]  = r["end"]
        else:
            merged.append(dict(r))
    return merged


def _make_result(start: float, end: float, spk: str, text: str) -> dict:
    return {"start": round(start, 2), "end": round(end, 2),
            "speaker": spk, "text": text.strip()}


def _sec_to_srt(sec: float) -> str:
    h  = int(sec // 3600)
    m  = int((sec % 3600) // 60)
    s  = int(sec % 60)
    ms = int(round((sec % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(results: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(results, 1):
        if not r["text"]:
            continue
        blocks.append(
            f"{i}\n"
            f"{_sec_to_srt(r['start'])} --> {_sec_to_srt(r['end'])}\n"
            f"{r['speaker']}: {r['text']}\n"
        )
    return "\n".join(blocks)


def print_results(results: list[dict]) -> None:
    print("\n" + "═" * 64)
    print("  完整对话")
    print("═" * 64)
    for r in results:
        if r["text"] and not r["text"].startswith("[ERROR"):
            dur = r["end"] - r["start"]
            print(f"\n  [{r['start']:6.2f}s → {r['end']:5.2f}s | {dur:.1f}s]  {r['speaker']}")
            print(f"  {r['text']}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# §8  主流程
# ══════════════════════════════════════════════════════════════════════════════

def _part_label(offsets: list[float], sec: float, names: list[str]) -> str:
    """根据时间戳判断属于第几个 part（用于 SRT 注释）。"""
    for i in range(len(offsets) - 1, -1, -1):
        if sec >= offsets[i]:
            return names[i]
    return names[0]


def to_srt_multipart(
    results: list[dict],
    offsets: list[float] | None = None,
    part_names: list[str] | None = None,
) -> str:
    """
    生成 SRT。若传入 offsets/part_names，在每个 part 切换处
    插入空白字幕分隔条（方便定位）。
    """
    blocks: list[str] = []
    idx = 1
    last_part = ""

    # 插入 part 分隔标记
    def maybe_insert_separator(sec: float) -> None:
        nonlocal idx, last_part
        if offsets and part_names:
            lbl = _part_label(offsets, sec, part_names)
            if lbl != last_part:
                if last_part:   # 不在第一段插入（避免冗余）
                    sep_ts = _sec_to_srt(sec)
                    blocks.append(f"{idx}\n{sep_ts} --> {sep_ts}\n── {lbl} ──\n")
                    idx += 1
                last_part = lbl

    for r in results:
        if not r["text"]:
            continue
        maybe_insert_separator(r["start"])
        blocks.append(
            f"{idx}\n"
            f"{_sec_to_srt(r['start'])} --> {_sec_to_srt(r['end'])}\n"
            f"{r['speaker']}: {r['text']}\n"
        )
        idx += 1
    return "\n".join(blocks)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="语音转写 + 说话人识别  （支持单文件 / 多文件拼接）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("audio", nargs="+",
                        help="一个或多个音频文件；多个文件按顺序拼接后统一处理")
    parser.add_argument("-s", "--speakers", dest="n_speakers",
                        type=int, default=0, metavar="N",
                        help="说话人数量（默认 0 = 自动检测）")
    parser.add_argument("--parallel",  action="store_true")
    parser.add_argument("--workers",   type=int, default=MAX_WORKERS_DEFAULT)
    parser.add_argument("--no-merge",  action="store_true",
                        help="不合并同说话人相邻段，保留原始分段")
    parser.add_argument("-o", "--output", default=None,
                        help="输出文件名前缀（不含扩展名）；默认取第一个文件名")
    args = parser.parse_args()

    if not API_KEY:
        print("错误：未设置 OPENAI_API_KEY。")
        print("请在 .env 文件中设置，或通过环境变量传入：")
        print("  export OPENAI_API_KEY=sk-xxx")
        sys.exit(1)

    multi = len(args.audio) > 1
    mode  = "并发（二阶修正）" if args.parallel else "流式（上下文 prompt）"

    print(f"\n{'='*64}")
    if multi:
        print(f"  模式    : 多文件拼接 → 统一处理（{len(args.audio)} 个 part）")
        for i, f in enumerate(args.audio, 1):
            print(f"  Part {i:2d} : {Path(f).name}")
    else:
        print(f"  文件    : {Path(args.audio[0]).name}")
    spk_mode = f"{args.n_speakers} 人（手动）" if args.n_speakers > 0 else "自动检测"
    print(f"  说话人  : {spk_mode}")
    print(f"  模型    : {MODEL}")
    print(f"  转写    : {mode}" + (f"  workers={args.workers}" if args.parallel else ""))
    print(f"{'='*64}\n")

    t0 = time.perf_counter()

    # ── 1. 预处理音频 ─────────────────────────────────────────────────────────
    print("▶ [1/4] 预处理音频...")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        wav_path = tf.name

    offsets: list[float] = [0.0]
    part_names: list[str] = []

    if multi:
        part_names = [f"Part {i+1}" for i in range(len(args.audio))]
        print(f"  拼接 {len(args.audio)} 个文件...")
        offsets = concat_parts_to_wav(args.audio, wav_path)
        for i, (name, off) in enumerate(zip(part_names, offsets)):
            print(f"    {name}: 起始 {off/60:.1f} min  ({Path(args.audio[i]).name})")
    else:
        to_wav(args.audio[0], wav_path)

    samples, sr = load_pcm(wav_path)
    total_min = len(samples) / sr / 60
    print(f"  总时长: {total_min:.1f} min   采样率: {sr} Hz\n")

    # ── 2. VAD ───────────────────────────────────────────────────────────────
    print("▶ [2/4] VAD 分割...")
    segs = vad_segments(samples, sr)
    print(f"  检测到 {len(segs)} 个语音段\n")
    if not segs:
        print("❌ 未检测到语音段")
        os.unlink(wav_path); return

    # ── 3. 说话人特征 + 聚类 + 平滑（全局） ────────────────────────────────
    print("▶ [3/4] 说话人特征（MFCC+Δ+ΔΔ+F0+谱）+ 全局聚类 + 时序平滑...")
    embs = build_embeddings_parallel(samples, sr, segs)

    if args.n_speakers > 0:
        n_cls = min(args.n_speakers, len(segs))
        print(f"  手动指定 {n_cls} 位说话人")
    else:
        print("  自动检测说话人数量...")
        n_cls = auto_detect_speakers(embs, segs, min_spk=1, max_spk=8)
        print(f"  → 检测结果: {n_cls} 位说话人")

    labels_raw    = assign_speakers(embs, n_cls) if len(segs) >= n_cls else [0] * len(segs)
    labels        = smooth_speaker_labels(list(labels_raw), segs)
    speaker_names = [f"Speaker {chr(65 + i)}" for i in range(n_cls)]

    changed = sum(1 for a, b in zip(labels_raw, labels) if a != b)
    print(f"  聚类: {n_cls} 位说话人  时序平滑修正: {changed} 段\n")

    # ── 4. 转写 ───────────────────────────────────────────────────────────────
    print("▶ [4/4] 转写...\n")
    t_tx = time.perf_counter()
    if args.parallel:
        results = asyncio.run(
            transcribe_parallel_async(wav_path, segs, labels, speaker_names, args.workers)
        )
        print("\n" + "─" * 64)
        for r in results:
            if r["text"]:
                print(f"[{r['start']:7.1f}s]  {r['speaker']}: {r['text']}")
        print("─" * 64)
    else:
        results = transcribe_sequential(wav_path, segs, labels, speaker_names)

    tx_time = time.perf_counter() - t_tx
    total   = time.perf_counter() - t0

    # ── 5. 后处理：合并同说话人相邻段 ─────────────────────────────────────────
    raw_count = len(results)
    if not args.no_merge:
        results = merge_consecutive_speakers(results)
        if len(results) < raw_count:
            print(f"\n  后处理合并: {raw_count} 段 → {len(results)} 段（同说话人相邻段）")

    # ── 6. 保存 ───────────────────────────────────────────────────────────────
    if args.output:
        stem = args.output
    elif multi:
        stem = "TTC_meeting"
    else:
        stem = Path(args.audio[0]).stem + "_transcript"

    srt_path  = stem + ".srt"
    json_path = stem + ".json"
    txt_path  = stem + ".txt"

    # SRT（带 Part 分隔条）
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(to_srt_multipart(results,
                                  offsets if multi else None,
                                  part_names if multi else None))

    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # TXT（人类可读）
    txt_lines: list[str] = []
    if multi:
        for i, (name, off) in enumerate(zip(part_names, offsets)):
            next_off = offsets[i + 1] if i + 1 < len(offsets) else float("inf")
            seg_results = [r for r in results if off <= r["start"] < next_off]
            txt_lines += ["", f"\n{'='*60}", f"  {name}  ({off/60:.1f} min ~ )", f"{'='*60}", ""]
            for r in seg_results:
                if r["text"] and "[ERROR" not in r["text"]:
                    txt_lines.append(f"[{_sec_to_srt(r['start'])}]  {r['speaker']}: {r['text']}")
                    txt_lines.append("")
    else:
        for r in results:
            if r["text"] and "[ERROR" not in r["text"]:
                txt_lines.append(f"[{_sec_to_srt(r['start'])}]  {r['speaker']}: {r['text']}")
                txt_lines.append("")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))

    word_count = sum(len(r["text"]) for r in results if "[ERROR" not in r["text"])
    error_count = sum(1 for r in results if "[ERROR" in r.get("text", ""))

    print(f"\n✅ 完成！转写: {tx_time:.1f}s   总计: {total:.1f}s")
    print(f"   字数: {word_count}   错误段: {error_count}")
    print(f"   SRT  → {srt_path}")
    print(f"   TXT  → {txt_path}")
    print(f"   JSON → {json_path}")
    print_results(results)

    os.unlink(wav_path)


if __name__ == "__main__":
    main()
