import { useState, useRef, useEffect } from "react";
import { Calendar, Clock, Users, Download, ChevronDown } from "lucide-react";
import { useExport } from "../../hooks/use-export";
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
  const [exportOpen, setExportOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { download } = useExport(meeting.id);

  // Close dropdown on outside click
  useEffect(() => {
    if (!exportOpen) return;
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setExportOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [exportOpen]);

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
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setExportOpen(!exportOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] text-text-secondary border border-border-subtle rounded-sm hover:bg-surface-hover transition-colors"
          >
            <Download size={13} />
            导出
            <ChevronDown size={11} className="ml-0.5 opacity-50" />
          </button>

          {exportOpen && (
            <div className="absolute right-0 top-full mt-1 w-44 bg-raised border border-border-subtle rounded-sm shadow-lg z-50 py-1">
              <button
                onClick={() => {
                  download("srt");
                  setExportOpen(false);
                }}
                className="w-full text-left px-3 py-2 text-[12px] text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
              >
                逐字稿 (SRT)
              </button>
              <button
                onClick={() => {
                  download("txt");
                  setExportOpen(false);
                }}
                className="w-full text-left px-3 py-2 text-[12px] text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
              >
                逐字稿 (TXT)
              </button>
              <button
                onClick={() => {
                  download("summary");
                  setExportOpen(false);
                }}
                className="w-full text-left px-3 py-2 text-[12px] text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
              >
                会议纪要
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
