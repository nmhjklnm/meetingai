# MeetingAI 产品重写设计文档

## 概述

对 MeetingAI 进行前后端完整重写：侧边栏导航、多录音会议管理、解析流程可视化、双栏逐字稿+纪要展示、导出下载。视觉参照腾讯会议，风格为 Vercel 风乳白玻璃暗色主题。

## 设计决策

### 架构策略

保留已验证的后端服务层（`services/`）和 ML 微服务（`ml_services/`），重写 API 路由、数据模型、Celery 任务和整个前端。

| 层 | 动作 |
|---|---|
| `services/` (VAD / Diarization / Transcription / NLP) | 保留 |
| `ml_services/` (vad_service / diarization_service) | 保留 |
| `models/` | 重写：新增 Recording 表 |
| `api/routes/` | 重写：适配多录音流程 |
| `worker/tasks.py` | 重写：加入录音合并步骤 |
| `core/` (config / database / redis) | 微调 |
| `frontend/` | 全部重写 |

### 多录音流程

用户先创建会议 → 逐个添加录音（1-4 个）→ 手动点击"开始解析"触发处理。会议在 `draft` 状态下可自由管理录音，触发处理后进入 `processing`。

---

## 数据模型

### Meeting

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String (UUID) | PK |
| title | String | 会议名称 |
| status | Enum | draft / processing / done / failed（注：替换现有的 pending，draft 更准确描述"用户管理录音"阶段） |
| audio_duration | Float | 合并后总时长（秒） |
| num_speakers | Integer | 说话人数 |
| summary | JSON | 摘要/行动项/关键词 |
| error_message | Text | 失败原因 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

关联：recordings[] / segments[] / speakers[]

### Recording（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | PK，自增 |
| meeting_id | String (FK) | 关联 Meeting，CASCADE 删除 |
| filename | String | 原始文件名 |
| file_path | String | 存储路径 |
| file_size | BigInteger | 字节数 |
| duration | Float | 时长（秒） |
| order | Integer | 排序序号 |
| uploaded_at | DateTime | 上传时间 |

### Segment（保留结构）

| 字段 | 类型 |
|------|------|
| id | Integer PK |
| meeting_id | String FK |
| start | Float |
| end | Float |
| speaker_id | String |
| text | Text |

### Speaker（保留结构）

| 字段 | 类型 |
|------|------|
| id | Integer PK |
| meeting_id | String FK |
| speaker_id | String |
| name | String |

---

## API 设计

### REST 端点

| 方法 | 路径 | 说明 | 请求 | 响应 |
|------|------|------|------|------|
| POST | `/api/meetings` | 创建会议 | `{title}` | Meeting (draft) |
| GET | `/api/meetings` | 会议列表 | — | MeetingListItem[] |
| GET | `/api/meetings/{id}` | 会议详情 | — | Meeting + recordings + segments + speakers |
| DELETE | `/api/meetings/{id}` | 删除会议 | — | 204 |
| POST | `/api/meetings/{id}/recordings` | 上传录音 | multipart file | Recording |
| DELETE | `/api/meetings/{id}/recordings/{rid}` | 删除录音 | — | 204 |
| POST | `/api/meetings/{id}/process` | 触发解析（draft/failed 状态可调用） | `{context?}` | 202 |
| PATCH | `/api/meetings/{id}/speakers` | 重命名说话人 | `[{speaker_id, name}]` | Speaker[] |
| GET | `/api/meetings/{id}/export/{fmt}` | 导出 srt/txt | — | 文件流 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `WS /ws/meetings/{id}/progress` | 实时进度推送 |

进度 JSON 格式：

```json
{
  "step": 4,
  "total_steps": 6,  // 与 pipeline 表一致
  "step_name": "transcription",
  "percent": 67,
  "sub_done": 134,
  "sub_total": 200,
  "eta_seconds": 120,
  "status": "processing"
}
```

---

## Celery Pipeline（6 步）

任务签名：`process_meeting_task(meeting_id: str)`

| 步骤 | 名称 | step_name | 操作 | 进度区间 |
|------|------|-----------|------|---------|
| 1 | 合并录音 | merge | 按 recording.order 排序，ffmpeg concat → `{audio_dir}/{meeting_id}_merged.wav`（16kHz mono）。单录音时仅格式转换。 | 0-5% |
| 2 | 语音检测 | vad | HTTP POST merged WAV → VAD 微服务 `/detect` | 5-15% |
| 3 | 说话人识别 | diarization | HTTP POST merged WAV + segments → Diarization 微服务 `/diarize` | 15-30% |
| 4 | 语音转写 | transcription | `TranscriptionService.transcribe_batch()`，20 路并发，`on_progress` 回调更新子进度 | 30-85% |
| 5 | 智能摘要 | nlp | `NLPService.analyze(transcript)` | 85-95% |
| 6 | 保存结果 | save | 清除旧 segments/speakers → 批量写入 → Meeting.status='done' | 95-100% |

合并后的 WAV 文件存储在 `{audio_dir}/{meeting_id}_merged.wav`，处理完成后保留（供后续导出/重处理使用）。

### 失败与重试

- 任何步骤失败：Meeting.status → `failed`，error_message 记录原因
- 用户可在 UI 点击"重试"：`POST /api/meetings/{id}/process` 重新触发，清除旧结果后从步骤 1 重跑
- 重试时 Meeting.status 从 `failed` → `processing`

---

## 前端架构

### 技术栈

- React 18 + TypeScript + Vite
- TailwindCSS（自定义暗色 token）
- React Query（服务端状态）
- React Router v6（`/` + `/meetings/:id`）
- Lucide React（图标）
- Axios + WebSocket

### 目录结构

```
src/
├── app.tsx                     # 路由 + QueryClient
├── main.tsx
├── index.css                   # Tailwind + CSS 变量
├── api/
│   ├── client.ts               # axios 实例 + WS 工厂
│   └── meetings.ts             # API 方法
├── hooks/
│   ├── use-meetings.ts         # React Query hooks
│   ├── use-progress.ts         # WebSocket 进度 hook
│   └── use-export.ts           # 导出 hook
├── types/
│   └── index.ts
├── components/
│   ├── layout/
│   │   ├── app-layout.tsx      # 三栏壳（sidebar + list + main）
│   │   ├── icon-sidebar.tsx    # 窄图标栏
│   │   └── meeting-list.tsx    # 会议列表面板
│   ├── meeting/
│   │   ├── detail-header.tsx   # 会议标题 + meta + 操作
│   │   ├── recording-manager.tsx  # 录音上传/管理
│   │   ├── processing-view.tsx    # 解析进度可视化
│   │   ├── timeline-panel.tsx     # 时间轴
│   │   ├── summary-panel.tsx      # 纪要 + 关键词 + 行动项
│   │   ├── transcript-panel.tsx   # 逐字稿
│   │   └── speaker-editor.tsx     # 说话人重命名
│   └── ui/
│       ├── button.tsx
│       ├── badge.tsx
│       ├── progress-bar.tsx
│       └── search-input.tsx
└── pages/
    └── meeting-page.tsx        # 状态驱动：draft → processing → done
```

### 状态驱动渲染

`meeting-page.tsx` 根据 `meeting.status` 渲染不同视图：

| Status | 渲染内容 |
|--------|---------|
| `draft` | `recording-manager` — 上传/管理录音 + 开始解析按钮 |
| `processing` | `processing-view` — 步骤条 + 进度 + ETA |
| `done` | 双栏：左 `timeline-panel` + `summary-panel`，右 `transcript-panel` |
| `failed` | 错误信息 + 重试按钮 |

### 路由

```
/                   → app-layout（默认选中第一个会议）
/meetings/:id       → app-layout（选中指定会议）
```

侧边栏始终可见，会议列表面板始终可见。点击列表项 = 切换右侧内容，无页面跳转。

---

## 视觉设计

### 色彩体系

纯黑底 + 乳白前景，零彩色（除错误状态），Vercel 风格。

| Token | 值 | 用途 |
|-------|------|------|
| `--bg-base` | `#09090b` | 主背景 |
| `--bg-raised` | `#111120` | 侧边栏/卡片 |
| `--bg-surface` | `rgba(255,255,255,0.02)` | 容器 |
| `--bg-hover` | `rgba(255,255,255,0.03)` | Hover |
| `--bg-active` | `rgba(255,255,255,0.04)` | Active/Selected |
| `--text-primary` | `rgba(255,255,250,0.85)` | 标题/正文 |
| `--text-secondary` | `rgba(255,255,250,0.5)` | 说明 |
| `--text-muted` | `rgba(255,255,250,0.25)` | 辅助/占位 |
| `--border-subtle` | `rgba(255,255,255,0.05)` | 分割线/边框 |
| `--border-focus` | `rgba(255,255,250,0.15)` | Focus/Hover 边框 |
| `--error` | `rgba(255,120,120,0.6)` | 失败状态 |

### 间距体系

4px 基准单位。允许值：4 / 8 / 12 / 16 / 24 / 32 / 40 / 48。

### 图标

Lucide 风格 SVG，统一 stroke-width 1.5，尺寸 14 / 18 / 24。禁止 emoji。

### 玻璃效果

容器 `backdrop-filter: blur(12px)` + 极细 border `rgba(255,255,255,0.04~0.08)`。

### 按钮

| 类型 | 样式 |
|------|------|
| Primary | 乳白实底 `rgba(255,255,250,0.9)` + 黑字 |
| Secondary | 玻璃底 + 细边框 + 乳白字 |
| Ghost | 透明 + 低透明度字 |

### 状态指示

- Done：亮点 `rgba(255,255,250,0.7)` + 微辉光
- Processing：呼吸动画 `opacity 1→0.3`
- Draft：暗点 `rgba(255,255,250,0.2)`
- Failed：偏红 `rgba(255,120,120,0.6)`

### Typography

Inter 字族，PingFang SC 回退。

| 角色 | 大小 | 权重 |
|------|------|------|
| Page title | 17px | 500 |
| Section label | 11px uppercase | 500 |
| Body | 13px | 400 |
| Meta | 11px | 400 |
| Small | 10px | 400 |

### Motion

仅用于解释层级和状态变化：
- Hover：`opacity` / `background` 过渡 0.12s
- 面板切换：无动画（即时切换）
- 进度条：`width transition 0.4s ease`
- 状态点呼吸：`opacity 2s infinite`（仅 processing）

禁止：装饰性动画、弹性过冲、页面级转场。

---

## 需要保留的后端代码

以下文件保留不改：

- `backend/services/vad/detector.py` — FSMN-VAD 检测器
- `backend/services/diarization/pipeline.py` — CAM++ 说话人分离
- `backend/services/transcription/transcriber.py` — GPT-4o 转写
- `backend/services/nlp/processor.py` — GPT-4o 摘要
- `backend/core/config.py` — 配置管理（微调：新增 `max_recordings_per_meeting=4`）
- `backend/core/database.py` — 数据库层
- `backend/core/redis_client.py` — Redis 进度
- `ml_services/vad_service.py` — VAD 微服务
- `ml_services/diarization_service.py` — 说话人分离微服务

## 需要重写的后端代码

- `backend/models/meeting.py` — 新增 Recording 模型
- `backend/api/routes/meetings.py` — 全新 REST 端点
- `backend/api/routes/websocket.py` — 进度格式更新
- `backend/api/main.py` — 路由注册
- `backend/worker/tasks.py` — 6 步 pipeline（含录音合并）

## 需要全部重写的前端

整个 `frontend/src/` 目录，按上述架构重新组织。

---

## Mockup 参考

设计 mockup 保存在 `.superpowers/brainstorm/92453-1773940085/`：
- `icon-system.html` — 图标系统 + 视觉语言 + 完整应用预览（最终版）
- `refined-v3.html` — 三场景布局（已完成/处理中/新建）
