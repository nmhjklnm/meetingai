import { useMemo } from "react";
import { Clock } from "lucide-react";
import { formatTime } from "../../lib/utils";
import type { Segment } from "../../types";

interface TimelinePanelProps {
  segments: Segment[];
}

export function TimelinePanel({ segments }: TimelinePanelProps) {
  const timeline = useMemo(() => {
    if (!segments.length) return [];
    const entries: { time: number; text: string }[] = [];
    let lastTime = -600; // force first entry
    for (const seg of segments) {
      if (seg.start - lastTime >= 600 && seg.text) {
        entries.push({ time: seg.start, text: seg.text.slice(0, 80) });
        lastTime = seg.start;
      }
    }
    return entries;
  }, [segments]);

  if (!timeline.length) return null;

  return (
    <div className="mb-8">
      {/* Section title */}
      <div className="flex items-center gap-2 mb-4">
        <Clock size={13} className="text-text-secondary" strokeWidth={1.5} />
        <span className="text-[11px] uppercase text-text-secondary font-medium tracking-[1px]">
          时间轴
        </span>
      </div>

      {/* Timeline */}
      <div className="relative pl-4">
        {/* Vertical line */}
        <div className="absolute left-[5px] top-1 bottom-1 w-px bg-[rgba(255,255,250,0.06)]" />

        <div className="space-y-4">
          {timeline.map((entry, i) => (
            <div key={i} className="relative flex items-start gap-3">
              {/* Dot */}
              <div
                className={`absolute left-[-12px] top-[5px] w-[5px] h-[5px] rounded-full border ${
                  i === 0
                    ? "bg-[rgba(255,255,250,0.5)] border-[rgba(255,255,250,0.15)]"
                    : "bg-[rgba(255,255,250,0.1)] border-[rgba(255,255,250,0.15)]"
                }`}
              />

              <div className="min-w-0">
                {/* Time badge */}
                <span className="text-[11px] font-semibold text-[rgba(255,255,250,0.35)] tabular-nums">
                  {formatTime(entry.time)}
                </span>
                {/* Text */}
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
