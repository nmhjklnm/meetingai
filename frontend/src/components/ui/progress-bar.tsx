import { cn } from "../../lib/utils";

interface ProgressBarProps {
  percent: number;
  className?: string;
}

export function ProgressBar({ percent, className }: ProgressBarProps) {
  return (
    <div
      className={cn(
        "h-1 bg-surface-active rounded-full overflow-hidden",
        className,
      )}
    >
      <div
        className="h-full bg-gradient-to-r from-[rgb(var(--fg)_/_0.5)] to-[rgb(var(--fg)_/_0.8)] rounded-full transition-[width] duration-[400ms] ease-out"
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}
