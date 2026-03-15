# 说话人分离算法升级指南

## 当前问题

现有算法（`transcribe_diarize.py`）说话人识别准确率只有 30-40%，根本原因：

| 问题 | 说明 |
|------|------|
| 特征不够判别 | MFCC 是声道形状特征，设计用于"识别词语"，而非"识别说话人" |
| 统计聚合损失时序 | 取 mean/std 把时序压扁，丢失韵律节奏等动态特征 |
| KMeans 假设球形簇 | 说话人 embedding 分布非球形 |
| 无监督 k 检测不稳定 | 轮廓系数在高维时效果差 |

## 升级路线图

### Phase 1：Resemblyzer（1-2天）

最快验证路径，精度中等，适合快速上线。

```bash
pip install resemblyzer
```

```python
from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import numpy as np

encoder = VoiceEncoder()

def get_embedding(wav_path: str, start: float, end: float) -> np.ndarray:
    wav = preprocess_wav(Path(wav_path))
    sr = 16000
    segment = wav[int(start * sr): int(end * sr)]
    return encoder.embed_utterance(segment)  # 256维

# 替换 transcribe_diarize.py 的 _embed_chunk()
```

**预期效果**：准确率提升到约 65-70%

---

### Phase 2：ECAPA-TDNN via SpeechBrain（推荐，3-5天）

生产级方案，准确率最高，本地推理无需 Token。

```bash
pip install speechbrain
```

```python
import torch
from speechbrain.pretrained import EncoderClassifier

# 首次运行自动下载 ~80MB 模型
classifier = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="models/weights/ecapa",
    run_opts={"device": "cpu"}  # 换 "cuda" 加速
)

def get_embedding(wav_tensor: torch.Tensor) -> np.ndarray:
    with torch.no_grad():
        emb = classifier.encode_batch(wav_tensor)
    return emb.squeeze().numpy()  # 192维
```

**聚类改进**：
```python
from scipy.cluster.hierarchy import linkage, fcluster

# 余弦距离 AHC，自动确定说话人数量
def cluster_embeddings(embs: np.ndarray, threshold: float = 0.4) -> np.ndarray:
    # L2 归一化 → 余弦距离 = 欧氏距离²/2
    normed = embs / np.linalg.norm(embs, axis=1, keepdims=True)
    Z = linkage(normed, method="average", metric="cosine")
    return fcluster(Z, t=threshold, criterion="distance") - 1
```

**预期效果**：准确率提升到约 85-90%

---

### Phase 3：pyannote.audio（端到端，可选）

业界最高精度，完整 Pipeline（VAD + 分割 + 嵌入 + 聚类），但需要 HuggingFace Token。

```bash
pip install pyannote.audio
```

```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token="YOUR_HF_TOKEN"
)

diarization = pipeline("audio.wav")
for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"{turn.start:.1f}s - {turn.end:.1f}s: {speaker}")
```

申请 HuggingFace Token：
1. 注册 https://huggingface.co
2. 接受 pyannote 模型协议
3. 生成 Token → 填入 `.env` 的 `HF_TOKEN`

**预期效果**：准确率 90%+，但推理速度较慢（~0.5x 实时）

---

## 性能对比

| 方案 | 说话人准确率 | 推理速度 | 模型大小 | 是否需要 Token |
|------|-------------|---------|---------|--------------|
| 当前 MFCC | 30-40% | 极快 | 无 | 否 |
| Resemblyzer | 65-70% | 快 | 25MB | 否 |
| ECAPA-TDNN | 85-90% | 中等 | 80MB | 否 |
| pyannote v3 | 90%+ | 较慢 | 200MB | 是（免费）|

## 集成到新架构

实现 `backend/services/diarization/pipeline.py` 中的 `TODO` 部分：
1. 完成 `_load_ecapa()` 方法
2. 完成 `embed()` 方法（输入 wav 片段，输出 192 维 embedding）
3. 完成 `diarize()` 方法（完整 Pipeline）
4. 完成 `auto_detect_num_speakers()` 方法（AHC + 阈值）
