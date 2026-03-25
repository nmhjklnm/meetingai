import { useRef, useState, useCallback, useEffect } from "react";
import { Music, Upload, X, Play, AlertCircle } from "lucide-react";
import type { Meeting, Recording } from "../../types";
import {
  useUploadRecording,
  useDeleteRecording,
  useStartProcessing,
} from "../../hooks/use-meetings";
import { useSettings } from "../../contexts/settings";

const ACCEPTED_TYPES = ".mp3,.wav,.m4a,.aac,.ogg,.flac,.wma,.webm";
const ACCEPTED_EXTENSIONS = new Set(ACCEPTED_TYPES.split(","));
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

/* ── Upload progress bar ─────────────────────────────────────────────── */

function UploadProgress({
  fileName,
  percent,
}: {
  fileName: string;
  percent: number;
}) {
  return (
    <div className="px-4 py-3 border border-border-subtle rounded-sm bg-surface space-y-2">
      <div className="flex items-center justify-between text-[13px]">
        <span className="text-text-primary truncate mr-2">{fileName}</span>
        <span className="text-text-muted flex-shrink-0">{percent}%</span>
      </div>
      <div className="h-1 bg-[rgb(var(--fg)_/_0.06)] rounded-full overflow-hidden">
        <div
          className="h-full bg-[rgb(var(--fg)_/_0.35)] rounded-full transition-[width] duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

/* ── Error toast ─────────────────────────────────────────────────────── */

function UploadError({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  return (
    <div className="flex items-start gap-2.5 px-4 py-3 border border-[var(--color-error)] rounded-sm bg-[rgba(255,80,80,0.06)]">
      <AlertCircle
        size={16}
        className="text-[var(--color-error)] flex-shrink-0 mt-0.5"
      />
      <div className="flex-1 min-w-0">
        <div className="text-[13px] text-text-primary">上传失败</div>
        <div className="text-[11px] text-text-muted mt-0.5">{message}</div>
      </div>
      <button
        onClick={onDismiss}
        className="text-text-muted hover:text-text-primary transition-colors flex-shrink-0 p-0.5"
      >
        <X size={14} />
      </button>
    </div>
  );
}

/* ── Main component ──────────────────────────────────────────────────── */

interface RecordingManagerProps {
  meeting: Meeting;
}

export function RecordingManager({ meeting }: RecordingManagerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const startMutation = useStartProcessing(meeting.id);
  const { settings } = useSettings();
  const [dragOver, setDragOver] = useState(false);

  // Upload state
  const [uploadPercent, setUploadPercent] = useState(0);
  const [uploadFileName, setUploadFileName] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);

  const uploadMutation = useUploadRecording(meeting.id, setUploadPercent);

  const remaining = MAX_RECORDINGS - meeting.recordings.length;
  const canUpload = remaining > 0 && !uploadMutation.isPending;
  const canStart = meeting.recordings.length > 0;
  const isUploading = uploadMutation.isPending;

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      setUploadError(null);
      const arr = Array.from(files).slice(0, remaining);
      for (const file of arr) {
        setUploadFileName(file.name);
        setUploadPercent(0);
        try {
          await uploadMutation.mutateAsync(file);
        } catch (err: unknown) {
          const msg =
            err instanceof Error ? err.message : "未知错误";
          // Try to extract server error detail
          const axiosErr = err as { response?: { data?: { detail?: string }; status?: number } };
          if (axiosErr?.response?.status === 413) {
            setUploadError("文件过大，超过服务器限制");
          } else if (axiosErr?.response?.data?.detail) {
            setUploadError(axiosErr.response.data.detail);
          } else if (msg.includes("Network Error") || msg.includes("timeout")) {
            setUploadError("网络错误或上传超时，请检查网络后重试");
          } else {
            setUploadError(`上传失败: ${msg}`);
          }
          break; // Stop uploading remaining files on error
        }
      }
      setUploadFileName("");
      setUploadPercent(0);
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

  // Clipboard paste
  useEffect(() => {
    if (!canUpload) return;
    const onPaste = (e: ClipboardEvent) => {
      const files = Array.from(e.clipboardData?.files ?? []).filter((f) => {
        const ext = "." + f.name.split(".").pop()?.toLowerCase();
        return ACCEPTED_EXTENSIONS.has(ext);
      });
      if (files.length > 0) {
        e.preventDefault();
        handleFiles(files);
      }
    };
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, [canUpload, handleFiles]);

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

      {/* Upload progress */}
      {isUploading && (
        <UploadProgress fileName={uploadFileName} percent={uploadPercent} />
      )}

      {/* Upload error */}
      {uploadError && (
        <UploadError
          message={uploadError}
          onDismiss={() => setUploadError(null)}
        />
      )}

      {/* Dropzone */}
      {canUpload && !isUploading && (
        <div
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            border-[1.5px] border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
            ${
              dragOver
                ? "border-[rgb(var(--fg)_/_0.25)] bg-[rgb(var(--fg)_/_0.01)]"
                : "border-[rgb(var(--fg)_/_0.1)] hover:border-[rgb(var(--fg)_/_0.2)] hover:bg-[rgb(var(--fg)_/_0.01)]"
            }
          `}
        >
          <Upload
            size={18}
            className="mx-auto text-text-muted mb-2"
          />
          <div className="text-[13px] text-text-secondary">
            拖放录音文件、粘贴、或点击选择
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
        onClick={() => startMutation.mutate({
          chat_model: settings.chatModel,
          transcription_model: settings.transcriptionModel,
          ...(settings.apiKey ? { api_key: settings.apiKey } : {}),
          ...(settings.baseUrl ? { base_url: settings.baseUrl } : {}),
        })}
        disabled={!canStart || startMutation.isPending || isUploading}
        className={`
          w-full flex items-center justify-center gap-2 px-4 py-3 rounded-sm text-[14px] font-medium transition-all
          ${
            canStart && !isUploading
              ? "bg-[rgb(var(--fg)_/_0.06)] text-cream border border-border-subtle hover:bg-[rgb(var(--fg)_/_0.1)]"
              : "bg-[rgb(var(--fg)_/_0.02)] text-text-muted border border-border-subtle opacity-50 cursor-not-allowed"
          }
        `}
      >
        <Play size={15} />
        {startMutation.isPending ? "正在启动..." : "开始解析"}
      </button>
    </div>
  );
}
