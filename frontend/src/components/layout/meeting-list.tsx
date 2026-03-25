import { useState, useRef, useEffect } from "react";
import { Plus, Trash2 } from "lucide-react";
import { cn } from "../../lib/utils";
import { formatDuration } from "../../lib/utils";
import { SearchInput } from "../ui/search-input";
import type { MeetingListItem, MeetingStatus } from "../../types";

function DeleteConfirm({
  title,
  onConfirm,
  onCancel,
}: {
  title: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onCancel();
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgb(var(--neutral)_/_0.3)]">
      <div
        ref={ref}
        className="bg-raised border border-border-subtle rounded-lg shadow-xl p-5 w-[300px] space-y-4"
      >
        <div className="text-[14px] text-text-primary font-medium">
          确定删除？
        </div>
        <div className="text-[12px] text-text-secondary leading-relaxed">
          「{title}」及其所有录音和转写结果将被永久删除，无法恢复。
        </div>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-[12px] text-text-secondary border border-border-subtle rounded-sm hover:bg-surface-hover transition-colors"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            className="px-3 py-1.5 text-[12px] text-[#fff] bg-[rgb(220_50_50_/_0.8)] hover:bg-[rgb(220_50_50_/_0.9)] rounded-sm transition-colors"
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
}

interface MeetingListProps {
  meetings: MeetingListItem[];
  selectedId?: string;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}

const statusDot: Record<MeetingStatus, string> = {
  done: "bg-[rgb(var(--fg)_/_0.7)] shadow-[0_0_6px_rgb(var(--fg)_/_0.2)]",
  processing: "bg-[rgb(var(--fg)_/_0.4)] animate-pulse",
  draft: "bg-[rgb(var(--fg)_/_0.2)]",
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
  onDelete,
}: MeetingListProps) {
  const [search, setSearch] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<MeetingListItem | null>(null);
  const filtered = search
    ? meetings.filter((m) =>
        m.title.toLowerCase().includes(search.toLowerCase()),
      )
    : meetings;

  return (
    <div className="w-[264px] bg-[rgb(var(--neutral)_/_0.01)] border-r border-border-subtle flex flex-col shrink-0">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 flex justify-between items-center">
        <span className="text-[15px] font-medium text-text-primary">
          会议
        </span>
        <button
          onClick={onCreate}
          className="w-7 h-7 rounded-sm bg-[rgb(var(--fg)_/_0.08)] grid place-items-center cursor-pointer hover:bg-[rgb(var(--fg)_/_0.12)] transition-colors"
        >
          <Plus
            className="w-3 h-3 text-[rgb(var(--fg)_/_0.8)]"
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
                "group px-3 py-3 rounded-md mb-0.5 cursor-pointer transition-colors border relative",
                active
                  ? "bg-[rgb(var(--neutral)_/_0.025)] border-[rgb(var(--neutral)_/_0.04)]"
                  : "border-transparent hover:bg-[rgb(var(--neutral)_/_0.015)]",
              )}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[13px] font-medium text-[rgb(var(--fg)_/_0.8)] truncate pr-5">
                  {m.title}
                </span>
                <span
                  className={cn(
                    "w-[5px] h-[5px] rounded-full shrink-0 ml-2 group-hover:hidden",
                    statusDot[m.status],
                  )}
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteTarget(m);
                  }}
                  className="hidden group-hover:grid w-5 h-5 place-items-center shrink-0 ml-2 rounded text-text-muted hover:text-error hover:bg-[rgb(var(--fg)_/_0.06)] transition-colors"
                  title="删除会议"
                >
                  <Trash2 size={12} />
                </button>
              </div>
              <div className="text-[11px] text-[rgb(var(--fg)_/_0.2)]">
                {buildMeta(m)}
              </div>
            </div>
          );
        })}
      </div>

      {deleteTarget && (
        <DeleteConfirm
          title={deleteTarget.title}
          onConfirm={() => {
            onDelete(deleteTarget.id);
            setDeleteTarget(null);
          }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
