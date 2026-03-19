import { useState } from "react";
import { Plus } from "lucide-react";
import { cn } from "../../lib/utils";
import { formatDuration } from "../../lib/utils";
import { SearchInput } from "../ui/search-input";
import type { MeetingListItem, MeetingStatus } from "../../types";

interface MeetingListProps {
  meetings: MeetingListItem[];
  selectedId?: string;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

const statusDot: Record<MeetingStatus, string> = {
  done: "bg-[rgba(255,255,250,0.7)] shadow-[0_0_6px_rgba(255,255,250,0.2)]",
  processing: "bg-[rgba(255,255,250,0.4)] animate-pulse",
  draft: "bg-[rgba(255,255,250,0.2)]",
  failed: "bg-error",
};

const statusLabel: Record<MeetingStatus, string> = {
  done: "已完成",
  processing: "处理中",
  draft: "待处理",
  failed: "失败",
};

function buildMeta(m: MeetingListItem): string {
  const parts: string[] = [];
  if (m.recording_count > 0) parts.push(`${m.recording_count} 段录音`);
  if (m.status === "done" && m.total_duration) {
    parts.push(formatDuration(m.total_duration));
  } else if (m.status !== "done") {
    parts.push(statusLabel[m.status]);
  }
  return parts.join(" \u00b7 ");
}

export function MeetingList({
  meetings,
  selectedId,
  onSelect,
  onCreate,
}: MeetingListProps) {
  const [search, setSearch] = useState("");
  const filtered = search
    ? meetings.filter((m) =>
        m.title.toLowerCase().includes(search.toLowerCase()),
      )
    : meetings;

  return (
    <div className="w-[264px] bg-[rgba(255,255,255,0.01)] border-r border-border-subtle flex flex-col shrink-0">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 flex justify-between items-center">
        <span className="text-[15px] font-medium text-text-primary">
          会议
        </span>
        <button
          onClick={onCreate}
          className="w-7 h-7 rounded-sm bg-[rgba(255,255,250,0.08)] grid place-items-center cursor-pointer hover:bg-[rgba(255,255,250,0.12)] transition-colors"
        >
          <Plus
            className="w-3 h-3 text-[rgba(255,255,250,0.8)]"
            strokeWidth={2.5}
          />
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pb-2">
        <SearchInput
          placeholder="搜索会议"
          value={search}
          onChange={setSearch}
        />
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 py-0.5">
        {filtered.map((m) => {
          const active = m.id === selectedId;
          return (
            <div
              key={m.id}
              onClick={() => onSelect(m.id)}
              className={cn(
                "px-3 py-3 rounded-md mb-0.5 cursor-pointer transition-colors border",
                active
                  ? "bg-[rgba(255,255,255,0.025)] border-[rgba(255,255,255,0.04)]"
                  : "border-transparent hover:bg-[rgba(255,255,255,0.015)]",
              )}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[13px] font-medium text-[rgba(255,255,250,0.8)] truncate">
                  {m.title}
                </span>
                <span
                  className={cn(
                    "w-[5px] h-[5px] rounded-full shrink-0 ml-2",
                    statusDot[m.status],
                  )}
                />
              </div>
              <div className="text-[11px] text-[rgba(255,255,250,0.2)]">
                {buildMeta(m)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
