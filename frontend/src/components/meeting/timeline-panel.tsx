import { useMemo } from "react";
import { Clock, RefreshCw, CheckCircle } from "lucide-react";
import { formatTime } from "../../lib/utils";
import type { RegenState } from "../../hooks/use-regenerate";
import type { Summary, Segment } from "../../types";

interface TimelinePanelProps {
  summary: Summary | null;
  segments: Segment[];
  regenState: RegenState;
  onRegenerate: () => void;
}

export function TimelinePanel({ summary, segments, regenState, onRegenerate }: TimelinePanelProps) {
  const timeline = useMemo(() => {
    if (summary?.timeline?.length) {
      return summary.timeline.map((e) => ({ time: e.time, text: e.title }));
    }
    if (!segments.length) return [];
    const entries: { time: number; text: string }[] = [];
    let lastTime = -600;
    for (const seg of segments) {
      if (seg.start - lastTime >= 600 && seg.text) {
        entries.push({ time: seg.start, text: seg.text.slice(0, 80) });
        lastTime = seg.start;
      }
    }
    return entries;
  }, [summary, segments]);

  if (!timeline.length) return null;

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Clock size={13} className="text-text-secondary" strokeWidth={1.5} />
          <span className="text-[11px] uppercase text-text-secondary font-medium tracking-[1px]">
            时间轴
          </span>
        </div>
        <button
          onClick={onRegenerate}
          disabled={regenState === "loading"}
          title="重新生成"
          className="p-1 rounded text-text-muted hover:text-text-secondary hover:bg-surface-hover transition-colors disabled:opacity-40"
        >
          {regenState === "loading" ? (
            <RefreshCw size={12} className="animate-spin" />
          ) : regenState === "done" ? (
            <CheckCircle size={12} className="text-[rgb(80_200_120)]" />
          ) : (
            <RefreshCw size={12} />
          )}
        </button>
      </div>

      <div className="relative pl-4">
        <div className="absolute left-[5px] top-1 bottom-1 w-px bg-[rgb(var(--fg)_/_0.06)]" />
        <div className="space-y-4">
          {timeline.map((entry, i) => (
            <div key={i} className="relative flex items-start gap-3">
              <div
                className={`absolute left-[-12px] top-[5px] w-[5px] h-[5px] rounded-full border ${
                  i === 0
                    ? "bg-[rgb(var(--fg)_/_0.5)] border-[rgb(var(--fg)_/_0.15)]"
                    : "bg-[rgb(var(--fg)_/_0.1)] border-[rgb(var(--fg)_/_0.15)]"
                }`}
              />
              <div className="min-w-0">
                <span className="text-[11px] font-semibold text-[rgb(var(--fg)_/_0.35)] tabular-nums">
                  {formatTime(entry.time)}
                </span>
                <div className="text-[12px] text-text-secondary leading-[1.65] mt-0.5">
                  {entry.text}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
