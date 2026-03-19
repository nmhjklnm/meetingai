import { cn } from "../../lib/utils";

interface ProgressBarProps {
  percent: number;
  className?: string;
}

export function ProgressBar({ percent, className }: ProgressBarProps) {
  return (
    <div
      className={cn(
        "h-1 bg-[rgba(255,255,255,0.04)] rounded-full overflow-hidden",
        className,
      )}
    >
      <div
        className="h-full bg-gradient-to-r from-[rgba(255,255,250,0.5)] to-[rgba(255,255,250,0.8)] rounded-full transition-[width] duration-[400ms] ease-out"
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}
