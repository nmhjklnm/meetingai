import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

interface BadgeProps {
  children: ReactNode;
  className?: string;
}

export function Badge({ children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "bg-[rgba(255,255,250,0.03)] border border-[rgba(255,255,250,0.05)] rounded-full px-2 py-0.5 text-[11px] text-text-secondary inline-flex items-center",
        className,
      )}
    >
      {children}
    </span>
  );
}
