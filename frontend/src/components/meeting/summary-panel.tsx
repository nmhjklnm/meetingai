import { FileText } from "lucide-react";
import { Badge } from "../ui/badge";
import type { Summary } from "../../types";

interface SummaryPanelProps {
  summary: Summary | null;
}

export function SummaryPanel({ summary }: SummaryPanelProps) {
  return (
    <div>
      {/* Section title */}
      <div className="flex items-center gap-2 mb-4">
        <FileText size={13} className="text-text-secondary" strokeWidth={1.5} />
        <span className="text-[11px] uppercase text-text-secondary font-medium tracking-[1px]">
          纪要
        </span>
      </div>

      {!summary ? (
        <div className="text-[12px] text-text-muted">暂无纪要</div>
      ) : (
        <div className="bg-[rgb(var(--neutral)_/_0.015)] border border-border-subtle rounded-lg p-5 space-y-5">
          {/* Summary text */}
          {summary.summary && (
            <p className="text-[13px] text-text-secondary leading-[1.8]">
              {summary.summary}
            </p>
          )}

          {/* Keywords */}
          {summary.keywords && summary.keywords.length > 0 && (
            <div>
              <span className="text-[11px] uppercase text-text-muted font-medium tracking-[1px] block mb-2">
                关键词
              </span>
              <div className="flex flex-wrap gap-1.5">
                {summary.keywords.map((kw, i) => (
                  <Badge key={i}>{kw}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Action items */}
          {summary.action_items && summary.action_items.length > 0 && (
            <div>
              <span className="text-[11px] uppercase text-text-muted font-medium tracking-[1px] block mb-2">
                行动项
              </span>
              <div className="space-y-2">
                {summary.action_items.map((item, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    {/* Checkbox outline */}
                    <div className="w-[13px] h-[13px] rounded-[2px] border border-[rgb(var(--fg)_/_0.12)] shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <span className="text-[11px] font-semibold text-[rgb(var(--fg)_/_0.55)]">
                        {item.assignee}
                      </span>
                      <span className="text-[12px] text-text-secondary ml-1.5">
                        {item.task}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
