# MeetingAI 产品重写 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite MeetingAI with multi-recording meetings, sidebar navigation, processing visualization, and Vercel-style dark glass UI.

**Architecture:** Keep existing ML services (`services/`, `ml_services/`). Rewrite data models (add Recording), API routes (separate create/upload/process), Celery worker (6-step with merge), and entire frontend (React + TailwindCSS with custom dark tokens).

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.0 / Celery / React 18 / TypeScript / TailwindCSS / React Query / Lucide React / Axios / WebSocket

**Spec:** `docs/superpowers/specs/2026-03-19-meetingai-rewrite-design.md`

**Visual Reference:** `.superpowers/brainstorm/92453-1773940085/icon-system.html`

---

## Task 1: Backend — Data Models

**Files:**
- Modify: `backend/models/meeting.py`
- Modify: `backend/models/__init__.py`
- Modify: `backend/core/config.py`

- [ ] **Step 1: Update config — add `max_recordings_per_meeting`**

In `backend/core/config.py`, add to `Settings`:

```python
max_recordings_per_meeting: int = 4
```

- [ ] **Step 2: Rewrite `backend/models/meeting.py`**

Replace the entire file. Key changes:
- `Meeting.status` default: `"pending"` → `"draft"`
- Remove `Meeting.audio_path` (replaced by Recording table)
- Add `Recording` model with: `id`, `meeting_id` (FK), `filename`, `file_path`, `file_size`, `duration`, `order`, `uploaded_at`
- Add `Meeting.recordings` relationship
- Keep `Segment` and `Speaker` unchanged

```python
"""
Data models: Meeting, Recording, Segment, Speaker
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名会议")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # draft | processing | done | failed

    audio_duration: Mapped[Optional[float]] = mapped_column(Float)
    num_speakers: Mapped[Optional[int]] = mapped_column(Integer)
    summary: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    recordings: Mapped[list[Recording]] = relationship(
        "Recording", back_populates="meeting", cascade="all, delete-orphan",
        order_by="Recording.order",
    )
    segments: Mapped[list[Segment]] = relationship(
        "Segment", back_populates="meeting", cascade="all, delete-orphan",
        order_by="Segment.start",
    )
    speakers: Mapped[list[Speaker]] = relationship(
        "Speaker", back_populates="meeting", cascade="all, delete-orphan",
    )


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration: Mapped[Optional[float]] = mapped_column(Float)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="recordings")


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    start: Mapped[float] = mapped_column(Float, nullable=False)
    end: Mapped[float] = mapped_column(Float, nullable=False)
    speaker_id: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text)

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="segments")


class Speaker(Base):
    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    speaker_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="speakers")
```

- [ ] **Step 3: Update `backend/models/__init__.py`**

```python
from backend.models.meeting import Meeting, Recording, Segment, Speaker

__all__ = ["Meeting", "Recording", "Segment", "Speaker"]
```

- [ ] **Step 4: Delete old database and verify models load**

```bash
rm -f data/meeting.db
cd /Users/apple/Desktop/project/v1/文稿/project/meetingai
uv run python -c "
from backend.core.database import Base, get_engine
import backend.models
engine = get_engine()
Base.metadata.create_all(bind=engine)
print('Tables:', Base.metadata.tables.keys())
"
```

Expected: prints `dict_keys(['meetings', 'recordings', 'segments', 'speakers'])`

- [ ] **Step 5: Commit**

```bash
git add backend/models/ backend/core/config.py
git commit -m "feat: add Recording model, update Meeting status to draft"
```

---

## Task 2: Backend — API Routes

**Files:**
- Rewrite: `backend/api/routes/meetings.py`
- Modify: `backend/api/main.py` (minor)

- [ ] **Step 1: Rewrite `backend/api/routes/meetings.py`**

Complete rewrite with these endpoints:
- `POST /api/meetings` — create meeting with `{title}`, returns Meeting (draft)
- `GET /api/meetings` — list all, desc by created_at, include recording count
- `GET /api/meetings/{id}` — full detail with recordings + segments + speakers
- `DELETE /api/meetings/{id}` — delete meeting + all files
- `POST /api/meetings/{id}/recordings` — upload file, validate count ≤ 4, save to `{audio_dir}/{meeting_id}/{filename}`, create Recording record, get duration via ffprobe
- `DELETE /api/meetings/{id}/recordings/{rid}` — remove file + record
- `POST /api/meetings/{id}/process` — validate status in (draft, failed), validate ≥1 recording, set status=processing, dispatch Celery task
- `PATCH /api/meetings/{id}/speakers` — update speaker names (existing logic)
- `GET /api/meetings/{id}/export/srt` — existing SRT export
- `GET /api/meetings/{id}/export/txt` — existing TXT export
- `GET /api/meetings/{id}/export/summary` — **NEW**: export summary/minutes as formatted text (title, summary, keywords, action items, per-speaker points)
- `GET /api/meetings/{id}/export/summary` — **NEW**: export summary as formatted text

Key implementation details:
- Pydantic schemas: `RecordingOut`, `MeetingOut` (with `recordings` field), `MeetingListItem` (with `recording_count`, `total_duration`)
- File upload: save to `{audio_dir}/{meeting_id}/` subdirectory (not flat)
- Duration detection: use `ffprobe -v error -show_entries format=duration -of csv=p=0 {file}`
- Recording order: auto-increment based on max existing order + 1
- Process endpoint: `process_meeting_task.delay(meeting_id, context)`

- [ ] **Step 2: Update `backend/api/main.py`**

No structural changes needed — the router prefix `/api/meetings` stays. Just ensure the import path is correct after rewrite.

- [ ] **Step 3: Verify API starts without errors**

```bash
cd /Users/apple/Desktop/project/v1/文稿/project/meetingai
rm -f data/meeting.db
uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Test with curl:
```bash
# Create meeting
curl -X POST http://localhost:8000/api/meetings -H 'Content-Type: application/json' -d '{"title":"测试会议"}'
# Should return {"id":"...", "title":"测试会议", "status":"draft", ...}

# List meetings
curl http://localhost:8000/api/meetings
# Should return array with the meeting
```

- [ ] **Step 4: Commit**

```bash
git add backend/api/
git commit -m "feat: rewrite API routes for multi-recording meetings"
```

---

## Task 3: Backend — Celery Worker

**Files:**
- Rewrite: `backend/worker/tasks.py`

- [ ] **Step 1: Rewrite worker with 6-step pipeline**

Key changes from existing:
- Task signature: `process_meeting_task(meeting_id: str, context: str | None = None)` — no `audio_path` param, reads recordings from DB
- Step 1 (merge): read recordings from DB ordered by `order`, ffmpeg concat → `{audio_dir}/{meeting_id}_merged.wav`. Single recording → just format convert.
- Steps 2-6: same as existing but using new progress format with `step_name`
- Progress JSON now includes `step_name` field matching spec
- On failure: set Meeting.status = "failed", error_message
- On success: set Meeting.status = "done"
- Clean up: keep merged WAV (don't delete), delete temp files only

ffmpeg concat implementation:
```python
def _merge_recordings(recordings: list, output_path: str) -> str:
    """Merge multiple recordings into single 16kHz mono WAV."""
    if len(recordings) == 1:
        # Single file: just convert format
        return _to_wav(recordings[0].file_path, output_path)

    # Create concat list file
    fd, list_file = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        with open(list_file, "w") as f:
            for rec in recordings:
                # Each file needs format conversion first
                f.write(f"file '{rec.file_path}'\n")

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
             "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", output_path],
            check=True, capture_output=True,
        )
    finally:
        os.unlink(list_file)
    return output_path
```

- [ ] **Step 2: Verify Celery app config is correct**

Ensure `celery_app` still initializes correctly and can be imported:
```bash
uv run python -c "from backend.worker.tasks import celery_app; print(celery_app)"
```

- [ ] **Step 3: Commit**

```bash
git add backend/worker/
git commit -m "feat: rewrite Celery worker with 6-step merge pipeline"
```

---

## Task 4: Backend — WebSocket Update

**Files:**
- Modify: `backend/api/routes/websocket.py`

- [ ] **Step 1: Update WebSocket to handle new progress format**

Minor change: the WebSocket code is generic (reads JSON from Redis and forwards), so it works with any progress shape. No code changes needed — just verify the progress JSON shape from worker matches the spec:

```json
{
  "step": 4,
  "total_steps": 6,
  "step_name": "transcription",
  "percent": 67,
  "sub_done": 134,
  "sub_total": 200,
  "eta_seconds": 120,
  "status": "processing"
}
```

The WebSocket handler already forwards whatever Redis returns as-is. **No changes needed.**

- [ ] **Step 2: Commit (skip if no changes)**

---

## Task 5: Frontend — Project Setup & Design Tokens

**Files:**
- Modify: `frontend/package.json` (remove zustand, update deps)
- Rewrite: `frontend/tailwind.config.ts`
- Rewrite: `frontend/src/index.css`
- Rewrite: `frontend/src/types/index.ts`
- Rewrite: `frontend/src/api/client.ts`
- Rewrite: `frontend/src/api/meetings.ts`
- Rewrite: `frontend/src/main.tsx`
- Rewrite: `frontend/src/app.tsx`

- [ ] **Step 1: Update `package.json`**

Remove `zustand`. Keep all other deps. Run `npm install`.

- [ ] **Step 2: Rewrite `tailwind.config.ts` with design tokens**

```typescript
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#09090b",
        raised: "#111120",
        surface: "rgba(255,255,255,0.02)",
        "surface-hover": "rgba(255,255,255,0.03)",
        "surface-active": "rgba(255,255,255,0.04)",
        "text-primary": "rgba(255,255,250,0.85)",
        "text-secondary": "rgba(255,255,250,0.5)",
        "text-muted": "rgba(255,255,250,0.25)",
        "border-subtle": "rgba(255,255,255,0.05)",
        "border-focus": "rgba(255,255,250,0.15)",
        cream: "rgba(255,255,250,0.9)",
        "cream-hover": "rgba(255,255,250,1)",
        error: "rgba(255,120,120,0.6)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "PingFang SC", "sans-serif"],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 3: Rewrite `src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background: #09090b;
  color: rgba(255, 255, 250, 0.85);
  -webkit-font-smoothing: antialiased;
}

/* Scrollbar */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.12); border-radius: 2px; }
::-webkit-scrollbar-track { background: transparent; }
```

- [ ] **Step 4: Rewrite `src/types/index.ts`**

```typescript
export type MeetingStatus = "draft" | "processing" | "done" | "failed";

export interface Recording {
  id: number;
  meeting_id: string;
  filename: string;
  file_size: number;
  duration: number | null;
  order: number;
  uploaded_at: string;
}

export interface MeetingListItem {
  id: string;
  title: string;
  status: MeetingStatus;
  recording_count: number;
  total_duration: number | null;
  num_speakers: number | null;
  created_at: string;
}

export interface Speaker {
  speaker_id: string;
  name: string;
}

export interface Segment {
  id: number;
  start: number;
  end: number;
  speaker_id: string;
  speaker_name: string;
  text: string | null;
}

export interface ActionItem {
  assignee: string;
  task: string;
  deadline?: string;
}

export interface Summary {
  summary?: string;
  speakers?: Record<string, string[]>;
  action_items?: ActionItem[];
  keywords?: string[];
  error?: string;
}

export interface Meeting {
  id: string;
  title: string;
  status: MeetingStatus;
  audio_duration: number | null;
  num_speakers: number | null;
  summary: Summary | null;
  error_message: string | null;
  created_at: string;
  recordings: Recording[];
  speakers: Speaker[];
  segments: Segment[];
}

export interface Progress {
  step: number;
  total_steps: number;
  step_name: string;
  percent: number;
  sub_done?: number;
  sub_total?: number;
  eta_seconds?: number;
  status: string;
}
```

- [ ] **Step 5: Rewrite `src/api/client.ts`**

```typescript
import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,
});

export function createProgressWS(meetingId: string): WebSocket {
  const wsBase = BASE_URL.startsWith("http")
    ? BASE_URL.replace(/^http/, "ws").replace(/\/api$/, "")
    : `ws://${window.location.host}`;
  return new WebSocket(`${wsBase}/ws/meetings/${meetingId}/progress`);
}
```

- [ ] **Step 6: Rewrite `src/api/meetings.ts`**

All API methods matching new backend routes:
- `create(title)`, `list()`, `get(id)`, `remove(id)`
- `uploadRecording(meetingId, file)`, `removeRecording(meetingId, recordingId)`
- `startProcessing(meetingId, context?)`, `updateSpeakers(meetingId, speakers)`
- `exportUrl(meetingId, format: 'srt'|'txt'|'summary')` — returns URL string

- [ ] **Step 7: Rewrite `src/app.tsx` with routing + QueryClient**

```typescript
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "./components/layout/app-layout";
import { MeetingPage } from "./pages/meeting-page";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5000, retry: 1 } },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<MeetingPage />} />
            <Route path="meetings/:id" element={<MeetingPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 8: Update `src/main.tsx`**

Update import path from `./App` to `./app`:

```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: frontend setup — design tokens, types, API client, routing"
```

---

## Task 6: Frontend — UI Primitives

**Files:**
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/progress-bar.tsx`
- Create: `frontend/src/components/ui/search-input.tsx`
- Create: `frontend/src/lib/utils.ts`

- [ ] **Step 1: Create `src/lib/utils.ts`**

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}min`;
  return `${m}min`;
}

export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(0)} MB`;
}
```

- [ ] **Step 2: Create Button component**

Three variants: `primary` (cream bg, black text), `secondary` (glass + border), `ghost` (transparent). All use Lucide-compatible `children` for icon+text combos.

- [ ] **Step 3: Create Badge component**

Pill badge for keywords/status. Cream bg at 3%, subtle border, small text. Props: `children`, `variant?`.

- [ ] **Step 4: Create ProgressBar component**

Thin gradient bar with cream-white fill, animated width transition.

- [ ] **Step 5: Create SearchInput component**

Glass bg, subtle border, magnifier icon, placeholder text.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ui/ frontend/src/lib/
git commit -m "feat: UI primitives — button, badge, progress-bar, search-input, utils"
```

---

## Task 7: Frontend — Layout Shell

**Files:**
- Create: `frontend/src/components/layout/icon-sidebar.tsx`
- Create: `frontend/src/components/layout/meeting-list.tsx`
- Create: `frontend/src/components/layout/app-layout.tsx`
- Create: `frontend/src/hooks/use-meetings.ts`

- [ ] **Step 1: Create `src/hooks/use-meetings.ts`**

React Query hooks:
- `useMeetingList()` — `GET /meetings`, refetch every 5s for processing meetings
- `useMeeting(id)` — `GET /meetings/{id}`
- `useCreateMeeting()` — mutation
- `useDeleteMeeting()` — mutation, invalidates list
- `useUploadRecording(meetingId)` — mutation
- `useDeleteRecording(meetingId)` — mutation
- `useStartProcessing(meetingId)` — mutation
- `useUpdateSpeakers(meetingId)` — mutation

- [ ] **Step 2: Create `icon-sidebar.tsx`**

Narrow 56px sidebar with:
- Logo (mic SVG, 32px container, cream-white bg at 8% opacity)
- Nav items: "Meetings" (grid icon, active state with left bar indicator)
- Settings (gear icon, secondary)
- Spacer + user avatar at bottom

All icons from `lucide-react`: `Mic`, `LayoutGrid`, `Settings`.

Active state: `bg-[rgba(255,255,255,0.04)]` + 2px left indicator + brighter icon color.

- [ ] **Step 3: Create `meeting-list.tsx`**

264px panel with:
- Header: "会议" title + "+" button (cream bg)
- Search input
- Scrollable meeting list
- Each item: title + status dot + meta (recording count, duration)
- Active item: `bg-[rgba(255,255,255,0.025)]` + subtle border
- Status dots: done (bright cream + glow), processing (breathing animation), draft (dim), failed (red)
- Click handler: `navigate(`/meetings/${id}`)`
- "+" button: calls `useCreateMeeting` then navigates to new meeting

- [ ] **Step 4: Create `app-layout.tsx`**

Three-column flex layout:
- `icon-sidebar` (56px fixed)
- `meeting-list` (264px fixed)
- `<Outlet />` (flex-1)

Full height `h-screen`, no overflow on shell.

- [ ] **Step 5: Verify layout renders**

```bash
cd frontend && npm run dev
```

Open http://localhost:3000 — should see three-column layout with sidebar, meeting list, empty main area.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: layout shell — icon sidebar, meeting list, app layout"
```

---

## Task 8: Frontend — Meeting Page (State Machine)

**Files:**
- Create: `frontend/src/pages/meeting-page.tsx`
- Create: `frontend/src/components/meeting/recording-manager.tsx`
- Create: `frontend/src/components/meeting/detail-header.tsx`
- Create: `frontend/src/hooks/use-progress.ts`

- [ ] **Step 1: Create `src/hooks/use-progress.ts`**

WebSocket hook that:
- Connects when `meetingId` is provided and status is `processing`
- Parses `Progress` JSON from each message
- Disconnects on `status === "done"` or `"failed"`
- On "done": invalidates meeting query to trigger refetch
- Returns `{ progress: Progress | null, isConnected: boolean }`

- [ ] **Step 2: Create `detail-header.tsx`**

Top bar showing:
- Meeting title (editable for draft? — no, just display)
- Meta row: date, duration, speakers count (icons from lucide: Calendar, Clock, Users)
- Actions: Export dropdown (SRT/TXT/Summary), Share button (primary)
- Only show export/share when status === "done"

- [ ] **Step 3: Create `recording-manager.tsx`**

Shown when `meeting.status === "draft"`:
- Title input (large, underline style, editable)
- Recording list: each file with icon, name, size, duration, waveform bars, remove button
- Dropzone: dashed border, upload icon, drag/drop support, file input on click
- File validation: accept audio types, max 2GB, max 4 recordings
- Upload calls `useUploadRecording`, shows inline progress
- "开始解析" button: full-width primary, calls `useStartProcessing`
- Button disabled if 0 recordings

- [ ] **Step 4: Create `meeting-page.tsx`**

State-driven renderer:
```typescript
function MeetingPage() {
  const { id } = useParams();
  const { data: meetings } = useMeetingList();
  const meetingId = id || meetings?.[0]?.id;
  const { data: meeting } = useMeeting(meetingId);

  if (!meetingId) return <EmptyState />;  // No meetings yet
  if (!meeting) return <Loading />;

  return (
    <div className="flex flex-col h-full">
      <DetailHeader meeting={meeting} />
      {meeting.status === "draft" && <RecordingManager meeting={meeting} />}
      {meeting.status === "processing" && <ProcessingView meetingId={meeting.id} />}
      {meeting.status === "done" && <MeetingContent meeting={meeting} />}
      {meeting.status === "failed" && <FailedView meeting={meeting} />}
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: meeting page — state machine, recording manager, detail header"
```

---

## Task 9: Frontend — Processing View

**Files:**
- Create: `frontend/src/components/meeting/processing-view.tsx`

- [ ] **Step 1: Implement processing view**

Centered layout with:
- Step track: 6 circles connected by lines
  - Done steps: cream check icon, success bg
  - Current step: numbered, accent glow
  - Pending steps: numbered, dim
  - Connectors: done=cream, active=gradient, pending=dim
- Step names: 合并 / 检测 / 识别 / 转写 / 摘要 / 完成
- Progress card below:
  - Step label in human language (map `step_name` → Chinese)
  - Large percentage number (cream gradient text)
  - Progress bar (thin, gradient fill)
  - Meta: "已处理 X / Y 段" + "预计还需约 N 分钟"

Uses `useProgress(meetingId)` hook. When progress.status === "done", React Query auto-refetches meeting data.

- [ ] **Step 2: Visual verification**

Manually test by creating a meeting, uploading a recording, starting processing (requires ML services running). Verify step transitions render correctly.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/meeting/processing-view.tsx
git commit -m "feat: processing view — step track, progress bar, ETA"
```

---

## Task 10: Frontend — Meeting Content (Done State)

**Files:**
- Create: `frontend/src/components/meeting/timeline-panel.tsx`
- Create: `frontend/src/components/meeting/summary-panel.tsx`
- Create: `frontend/src/components/meeting/transcript-panel.tsx`
- Create: `frontend/src/components/meeting/speaker-editor.tsx`
- Create: `frontend/src/components/meeting/meeting-content.tsx`

- [ ] **Step 1: Create `meeting-content.tsx`**

Two-column layout (flex):
- Left panel (46%): `timeline-panel` + `summary-panel`, scrollable
- Right panel (flex-1): `transcript-panel`, scrollable
- Separator: 1px `border-subtle`

- [ ] **Step 2: Create `timeline-panel.tsx`**

Section title "时间轴" (Clock icon).
Vertical timeline with:
- Left line: 1px cream gradient
- Items: time badge + summary text
- Clickable: clicking a timeline item scrolls transcript to that timestamp
- Active item: highlighted bg + filled dot

Timeline data comes from `meeting.summary.speakers` or is generated from segments by grouping consecutive segments from same speaker into topic blocks. For MVP, use segment timestamps at ~10 min intervals.

- [ ] **Step 3: Create `summary-panel.tsx`**

Section title "纪要" (FileText icon).
Card with:
- Summary text paragraph
- Keywords row: pill badges (cream bg at 3% + border)
- Action items: checkbox-style rows with assignee name (brighter) + task text
- Each subsection has uppercase label

Data from `meeting.summary`.

- [ ] **Step 4: Create `transcript-panel.tsx`**

Section title "逐字稿" (MessageSquare icon) + search input.
Scrollable list of transcript entries:
- Speaker avatar circle (30px, initials, alternating colors for different speakers)
  - Speaker A: cream at 4% bg, 50% text
  - Speaker B: cream at 2.5% bg, 35% text
  - More speakers cycle through opacity variants
- Speaker name (colored) + timestamp
- Text body (13px, 1.75 line-height, primary text color)

Search: filter segments by text content, highlight matches.

Clicking a segment highlights it. Speaker names use `speaker_name` from API (which respects renamed speakers).

- [ ] **Step 5: Create `speaker-editor.tsx`**

Inline editor triggered from detail header or a dedicated panel:
- List speakers with current names
- Click name → inline text input → Enter to save, Escape to cancel
- Calls `useUpdateSpeakers` mutation
- On success: invalidates meeting query → transcript re-renders with new names

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/meeting/
git commit -m "feat: meeting content — timeline, summary, transcript, speaker editor"
```

---

## Task 11: Frontend — Export & Failed State

**Files:**
- Create: `frontend/src/hooks/use-export.ts`
- Create: `frontend/src/components/meeting/failed-view.tsx`
- Modify: `frontend/src/components/meeting/detail-header.tsx` (add export dropdown)

- [ ] **Step 1: Create `src/hooks/use-export.ts`**

```typescript
import { meetingsApi } from "../api/meetings";

export function useExport(meetingId: string) {
  const download = (format: "srt" | "txt" | "summary") => {
    const url = meetingsApi.exportUrl(meetingId, format);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${meetingId}.${format === "summary" ? "txt" : format}`;
    a.click();
  };
  return { download };
}
```

- [ ] **Step 2: Add export dropdown to detail header**

When meeting.status === "done", show export button that reveals dropdown:
- 导出逐字稿 (SRT)
- 导出逐字稿 (TXT)
- 导出会议纪要

Uses simple state toggle, no library needed.

- [ ] **Step 3: Create `failed-view.tsx`**

Centered message:
- Error icon (AlertCircle from lucide)
- "处理失败" title
- Error message from `meeting.error_message` (truncated, expandable)
- "重试" button (primary) — calls `useStartProcessing`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: export (SRT/TXT/summary) + failed state retry"
```

---

## Task 12: Frontend — Empty State & Polish

**Files:**
- Create: `frontend/src/components/meeting/empty-state.tsx`
- Modify: various components for polish

- [ ] **Step 1: Create empty state**

Shown when no meetings exist:
- Mic icon (large, dim)
- "还没有会议" text
- "创建第一个会议" primary button

- [ ] **Step 2: Polish pass**

- Verify all hover/focus states work
- Verify responsive behavior (sidebar collapses on narrow screens is NOT in scope — desktop only)
- Verify WebSocket reconnection on page refresh
- Verify meeting list auto-updates when processing completes
- Verify speaker rename updates transcript in real-time (React Query invalidation)

- [ ] **Step 3: Delete old unused frontend files**

Remove any files from the old frontend that are no longer referenced:
- `frontend/src/pages/UploadPage.tsx`
- `frontend/src/pages/MeetingsListPage.tsx`
- `frontend/src/pages/MeetingPage.tsx`
- `frontend/src/components/Layout.tsx`

- [ ] **Step 4: Final commit**

```bash
git add -A frontend/
git commit -m "feat: empty state, polish, remove old frontend files"
```

---

## Task 13: Integration Verification

- [ ] **Step 1: Start all services**

```bash
cd /Users/apple/Desktop/project/v1/文稿/project/meetingai
bash start_local.sh
# In another terminal:
cd frontend && npm run dev
```

- [ ] **Step 2: End-to-end test**

1. Open http://localhost:3000
2. Click "+" to create a meeting
3. Enter title "测试会议"
4. Upload 2 audio files
5. Click "开始解析"
6. Verify processing view shows step progress
7. Wait for completion
8. Verify timeline, summary, transcript render
9. Rename a speaker → verify transcript updates
10. Export SRT, TXT, and summary
11. Delete the meeting

- [ ] **Step 3: Final commit with any fixes**

```bash
git add -A
git commit -m "fix: integration fixes from end-to-end testing"
```
