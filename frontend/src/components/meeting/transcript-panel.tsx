import { useState, useMemo } from "react";
import { MessageSquare } from "lucide-react";
import { SearchInput } from "../ui/search-input";
import { formatTime } from "../../lib/utils";
import type { Meeting } from "../../types";

const SPEAKER_STYLES = [
  { bg: "rgb(var(--fg) / 0.04)", text: "rgb(var(--fg) / 0.5)", border: "rgb(var(--fg) / 0.06)" },
  { bg: "rgb(var(--fg) / 0.025)", text: "rgb(var(--fg) / 0.35)", border: "rgb(var(--fg) / 0.04)" },
  { bg: "rgb(var(--fg) / 0.05)", text: "rgb(var(--fg) / 0.55)", border: "rgb(var(--fg) / 0.07)" },
  { bg: "rgb(var(--fg) / 0.02)", text: "rgb(var(--fg) / 0.3)", border: "rgb(var(--fg) / 0.03)" },
];

function getInitials(name: string): string {
  if (!name) return "?";
  // For Chinese names, take the last 1-2 characters; for English, take initials
  const trimmed = name.trim();
  if (/[\u4e00-\u9fff]/.test(trimmed)) {
    return trimmed.slice(-1);
  }
  return trimmed
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

interface TranscriptPanelProps {
  meeting: Meeting;
}

export function TranscriptPanel({ meeting }: TranscriptPanelProps) {
  const [search, setSearch] = useState("");

  // Build speaker index map (deterministic order based on first appearance)
  const speakerIndexMap = useMemo(() => {
    const map = new Map<string, number>();
    let idx = 0;
    for (const seg of meeting.segments) {
      if (!map.has(seg.speaker_id)) {
        map.set(seg.speaker_id, idx);
        idx++;
      }
    }
    return map;
  }, [meeting.segments]);

  // Filter segments by search
  const filteredSegments = useMemo(() => {
    if (!search.trim()) return meeting.segments;
    const q = search.toLowerCase();
    return meeting.segments.filter(
      (seg) => seg.text && seg.text.toLowerCase().includes(q),
    );
  }, [meeting.segments, search]);

  return (
    <div>
      {/* Section title + search */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <MessageSquare
            size={13}
            className="text-text-secondary"
            strokeWidth={1.5}
          />
          <span className="text-[11px] uppercase text-text-secondary font-medium tracking-[1px]">
            逐字稿
          </span>
        </div>
        <SearchInput
          placeholder="搜索内容"
          value={search}
          onChange={setSearch}
          className="w-48"
        />
      </div>

      {/* Transcript entries */}
      <div className="space-y-4">
        {filteredSegments.length === 0 ? (
          <div className="text-[12px] text-text-muted py-8 text-center">
            {search ? "没有匹配的内容" : "暂无转写内容"}
          </div>
        ) : (
          filteredSegments.map((seg) => {
            const idx = speakerIndexMap.get(seg.speaker_id) ?? 0;
            const style = SPEAKER_STYLES[idx % SPEAKER_STYLES.length];

            return (
              <div key={seg.id} className="flex gap-3">
                {/* Avatar */}
                <div
                  className="w-[30px] h-[30px] rounded-full flex items-center justify-center text-[11px] font-semibold shrink-0"
                  style={{
                    backgroundColor: style.bg,
                    color: style.text,
                    border: `1px solid ${style.border}`,
                  }}
                >
                  {getInitials(seg.speaker_name)}
                </div>

                <div className="min-w-0 flex-1">
                  {/* Speaker + time */}
                  <div className="flex items-baseline gap-2">
                    <span
                      className="text-[12px] font-semibold"
                      style={{ color: style.text }}
                    >
                      {seg.speaker_name}
                    </span>
                    <span className="text-[10px] text-text-muted tabular-nums">
                      {formatTime(seg.start)}
                    </span>
                  </div>
                  {/* Text */}
                  <p className="text-[13px] text-text-primary leading-[1.75] mt-0.5">
                    {seg.text}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
