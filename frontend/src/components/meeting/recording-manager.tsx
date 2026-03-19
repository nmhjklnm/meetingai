import { useRef, useState, useCallback } from "react";
import { Music, Upload, X, Play } from "lucide-react";
import type { Meeting, Recording } from "../../types";
import {
  useUploadRecording,
  useDeleteRecording,
  useStartProcessing,
} from "../../hooks/use-meetings";

const ACCEPTED_TYPES = ".mp3,.wav,.m4a,.aac,.ogg,.flac,.wma,.webm";
const MAX_RECORDINGS = 10;

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function MiniWaveform() {
  const bars = [3, 5, 8, 4, 7, 3, 6, 4, 5, 3, 7, 5, 4, 6, 3];
  return (
    <div className="flex items-end gap-[2px] h-4 opacity-30">
      {bars.map((h, i) => (
        <div
          key={i}
          className="w-[2px] bg-cream rounded-full"
          style={{ height: `${h * 1.5}px` }}
        />
      ))}
    </div>
  );
}

interface RecordingItemProps {
  recording: Recording;
  meetingId: string;
}

function RecordingItem({ recording, meetingId }: RecordingItemProps) {
  const deleteMutation = useDeleteRecording(meetingId);
  const [hovered, setHovered] = useState(false);

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 border border-border-subtle rounded-sm bg-surface hover:bg-surface-hover transition-colors group"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <Music size={16} className="text-text-muted flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-[13px] text-text-primary truncate">
          {recording.filename}
        </div>
        <div className="text-[11px] text-text-muted mt-0.5 flex gap-2">
          <span>{formatFileSize(recording.file_size)}</span>
          {recording.duration != null && (
            <span>{formatDuration(recording.duration)}</span>
          )}
        </div>
      </div>
      <MiniWaveform />
      {hovered && (
        <button
          onClick={() => deleteMutation.mutate(recording.id)}
          disabled={deleteMutation.isPending}
          className="text-text-muted hover:text-error transition-colors flex-shrink-0 p-1"
          aria-label="移除录音"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

interface RecordingManagerProps {
  meeting: Meeting;
}

export function RecordingManager({ meeting }: RecordingManagerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadRecording(meeting.id);
  const startMutation = useStartProcessing(meeting.id);
  const [dragOver, setDragOver] = useState(false);

  const remaining = MAX_RECORDINGS - meeting.recordings.length;
  const canUpload = remaining > 0;
  const canStart = meeting.recordings.length > 0;

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const arr = Array.from(files).slice(0, remaining);
      for (const file of arr) {
        await uploadMutation.mutateAsync(file);
      }
    },
    [remaining, uploadMutation],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFiles(e.target.files);
        e.target.value = "";
      }
    },
    [handleFiles],
  );

  return (
    <div className="p-6 max-w-[640px] mx-auto space-y-5">
      {/* Title area */}
      <div className="text-[20px] font-medium text-text-primary tracking-tight">
        {meeting.title}
      </div>

      {/* Recording list */}
      {meeting.recordings.length > 0 && (
        <div className="space-y-2">
          {meeting.recordings.map((rec) => (
            <RecordingItem
              key={rec.id}
              recording={rec}
              meetingId={meeting.id}
            />
          ))}
        </div>
      )}

      {/* Dropzone */}
      {canUpload && (
        <div
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            border-[1.5px] border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
            ${
              dragOver
                ? "border-[rgba(255,255,250,0.25)] bg-[rgba(255,255,250,0.01)]"
                : "border-[rgba(255,255,250,0.1)] hover:border-[rgba(255,255,250,0.2)] hover:bg-[rgba(255,255,250,0.01)]"
            }
          `}
        >
          <Upload
            size={18}
            className="mx-auto text-text-muted mb-2"
          />
          <div className="text-[13px] text-text-secondary">
            {uploadMutation.isPending
              ? "上传中..."
              : "拖放录音文件，或点击选择"}
          </div>
          <div className="text-[11px] text-text-muted mt-1">
            MP3 / WAV / M4A / AAC &middot; 最大 2GB &middot; 还可添加{" "}
            {remaining} 个
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
      )}

      {/* Start button */}
      <button
        onClick={() => startMutation.mutate(undefined)}
        disabled={!canStart || startMutation.isPending}
        className={`
          w-full flex items-center justify-center gap-2 px-4 py-3 rounded-sm text-[14px] font-medium transition-all
          ${
            canStart
              ? "bg-[rgba(255,255,250,0.06)] text-cream border border-border-subtle hover:bg-[rgba(255,255,250,0.1)]"
              : "bg-[rgba(255,255,250,0.02)] text-text-muted border border-border-subtle opacity-50 cursor-not-allowed"
          }
        `}
      >
        <Play size={15} />
        {startMutation.isPending ? "正在启动..." : "开始解析"}
      </button>
    </div>
  );
}
