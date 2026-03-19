import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type Variant = "primary" | "secondary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-cream text-[#09090b] font-medium hover:bg-cream-hover",
  secondary:
    "bg-[rgba(255,255,255,0.03)] border border-border-subtle text-text-secondary hover:bg-surface-hover hover:border-border-focus hover:text-text-primary",
  ghost:
    "text-text-muted hover:text-text-secondary",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "secondary", className, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled}
      className={cn(
        "px-4 py-1.5 rounded-sm text-[12px] flex items-center gap-1 transition-all duration-[120ms] cursor-pointer",
        "disabled:opacity-40 disabled:pointer-events-none",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  ),
);

Button.displayName = "Button";
