import { Calendar, Clock, Users, Download, Share2 } from "lucide-react";
import type { Meeting } from "../../types";

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m} 分钟`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

interface DetailHeaderProps {
  meeting: Meeting;
}

export function DetailHeader({ meeting }: DetailHeaderProps) {
  const handleExport = () => {
    // Export functionality will be implemented in Task 11
  };

  const handleShare = () => {
    // Share functionality will be implemented in Task 11
  };

  return (
    <div className="px-6 py-3 border-b border-border-subtle flex justify-between items-center min-h-[56px]">
      <div>
        <div className="text-[17px] font-medium text-text-primary tracking-tight">
          {meeting.title}
        </div>
        <div className="flex gap-4 items-center text-[11px] text-text-muted mt-0.5">
          <span className="flex items-center gap-1">
            <Calendar size={12} />
            {formatDate(meeting.created_at)}
          </span>
          {meeting.audio_duration != null && (
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {formatDuration(meeting.audio_duration)}
            </span>
          )}
          {meeting.num_speakers != null && (
            <span className="flex items-center gap-1">
              <Users size={12} />
              {meeting.num_speakers} 位说话人
            </span>
          )}
        </div>
      </div>
      {meeting.status === "done" && (
        <div className="flex gap-2">
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] text-text-secondary border border-border-subtle rounded-sm hover:bg-surface-hover transition-colors"
          >
            <Download size={13} />
            导出
          </button>
          <button
            onClick={handleShare}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] text-cream bg-[rgba(255,255,250,0.06)] border border-border-subtle rounded-sm hover:bg-[rgba(255,255,250,0.1)] transition-colors"
          >
            <Share2 size={13} />
            分享
          </button>
        </div>
      )}
    </div>
  );
}
