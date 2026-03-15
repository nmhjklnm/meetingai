# Meeting Transcriber

> 会议语音转写 + 说话人分离 + 智能摘要服务
> 对标腾讯会议 / 飞书会议 / 钉钉会议的核心录音转录能力

---

## 功能概览

| 功能 | 状态 | 说明 |
|------|------|------|
| 语音转文字 | ✅ 已实现 | GPT-4o-transcribe，支持中英文 |
| 说话人分离 | 🔄 升级中 | ECAPA-TDNN 替代手工 MFCC（见下） |
| 摘要 & 行动项 | 🚧 规划中 | GPT-4o NLP 分析 |
| React 前端 | 🚧 规划中 | 上传、实时转写、查看结果 |
| REST API | 🚧 规划中 | FastAPI + WebSocket 进度推送 |
| 说话人姓名对齐 | 🚧 规划中 | 将 Speaker A/B 对齐到真实姓名 |

---

## 系统架构

```
┌──────────────────────────────────────────────────────┐
│                   React 前端 (Vite)                   │
│  上传音频 → 实时进度条 → 转录查看 → 摘要/行动项        │
└──────────────────────┬───────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼───────────────────────────────┐
│             FastAPI Gateway (Python)                   │
└──────┬───────────────┬──────────────────┬────────────┘
       │               │                  │
┌──────▼──────┐ ┌──────▼──────┐  ┌───────▼──────────┐
│ VAD Service │ │ Diarization │  │ Transcription    │
│ Silero VAD  │ │ ECAPA-TDNN  │  │ GPT-4o-transcribe│
│ (本地推理)  │ │ (本地推理)  │  │ (外部 API)       │
└─────────────┘ └─────────────┘  └──────────────────┘
                                          │
                               ┌──────────▼─────────┐
                               │   NLP Service       │
                               │  摘要/关键词/行动项  │
                               │   (GPT-4o)          │
                               └────────────────────┘
```

**存储层：**
- PostgreSQL — 会议记录、转录结果、用户数据
- Redis — Celery 任务队列、进度缓存
- 本地文件系统 / S3 — 音频文件存储

---

## 说话人识别升级（核心）

### 当前问题
手工 MFCC 特征 → KMeans 聚类，**准确率仅 30-40%**。

根本原因：MFCC 是 1970 年代为语音识别（"说了什么"）设计的特征，无法可靠区分不同人的音色。

### 升级方案：ECAPA-TDNN

| 对比项 | 旧方案 | 新方案 |
|-------|--------|--------|
| 特征 | 手工 MFCC + F0 统计（249维） | ECAPA-TDNN 神经网络（192维） |
| 训练数据 | 无（纯手工） | VoxCeleb（1M+ 语音段，7000+ 说话人）|
| 聚类 | KMeans（欧氏距离）| AHC + 余弦距离 + 自动阈值 |
| 准确率 | 30-40% | **85-90%** |

详见 [`docs/diarization-upgrade.md`](docs/diarization-upgrade.md)

---

## 快速开始（当前版本）

### 环境要求

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) 包管理器
- ffmpeg

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 复制环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 和 OPENAI_BASE_URL
```

### 转写单个音频

```bash
uv run python transcribe_diarize.py 会议录音.mp3 --parallel --workers 20
```

### 转写多文件会议（自动拼接）

```bash
uv run python transcribe_diarize.py part1.m4a part2.m4a part3.m4a \
  --parallel --workers 20 --output 完整会议
```

### 输出文件

| 文件 | 格式 | 说明 |
|------|------|------|
| `xxx_transcript.srt` | SRT 字幕 | 含说话人标签和时间轴 |
| `xxx_transcript.txt` | 纯文本 | 易于阅读的会议记录 |
| `xxx_transcript.json` | JSON | 结构化数据，含所有元信息 |

---

## 项目结构

```
.
├── transcribe_diarize.py        # 当前可用的命令行工具（v3）
├── pyproject.toml               # Python 依赖（uv 管理）
│
├── backend/                     # 新架构后端（重构中）
│   ├── api/                     # FastAPI 入口和路由
│   ├── services/
│   │   ├── vad/                 # Silero VAD
│   │   ├── diarization/         # ECAPA-TDNN 说话人分离
│   │   ├── transcription/       # 转写服务（GPT-4o-transcribe）
│   │   └── nlp/                 # 摘要、行动项提取
│   ├── models/                  # 数据库模型（SQLAlchemy）
│   └── worker/                  # Celery 异步任务
│
├── frontend/                    # React + TypeScript 前端（规划中）
│
├── docs/
│   └── diarization-upgrade.md  # 说话人识别升级技术文档
│
├── docker-compose.yml           # 完整服务编排
└── .env.example                 # 环境变量模板
```

---

## 开发路线图

### v1（当前）：命令行工具
- [x] VAD 分割（能量阈值）
- [x] 说话人分离（MFCC + KMeans）
- [x] 并发转写（GPT-4o-transcribe）
- [x] SRT / TXT / JSON 输出
- [x] 多文件拼接

### v2（进行中）：算法升级
- [ ] 集成 Resemblyzer（快速验证）
- [ ] 集成 Silero VAD
- [ ] 集成 ECAPA-TDNN（目标：85%+ 说话人准确率）
- [ ] 集成 pyannote.audio（可选）

### v3（规划中）：服务化
- [ ] FastAPI 后端 API
- [ ] PostgreSQL 数据持久化
- [ ] Celery 异步任务队列
- [ ] WebSocket 实时进度
- [ ] React 前端

### v4（规划中）：智能分析
- [ ] GPT-4o 会议摘要
- [ ] 行动项自动提取
- [ ] 说话人姓名对齐
- [ ] 多语言支持

---

## 贡献指南

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/ecapa-diarization`
3. 查看对应的 TODO 文件（`docs/diarization-upgrade.md`）
4. 提交 PR，描述改进和测试结果

---

## License

MIT
