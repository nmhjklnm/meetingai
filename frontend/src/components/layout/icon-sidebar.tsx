import { Mic, LayoutGrid, Settings } from "lucide-react";
import { cn } from "../../lib/utils";

interface NavItemProps {
  icon: typeof LayoutGrid;
  label?: string;
  active?: boolean;
}

function NavItem({ icon: Icon, active }: NavItemProps) {
  return (
    <div
      className={cn(
        "relative w-10 h-10 rounded-md grid place-items-center cursor-pointer transition-all duration-[120ms]",
        active
          ? "bg-surface-active text-[rgba(255,255,250,0.8)]"
          : "text-[rgba(255,255,250,0.2)] hover:text-[rgba(255,255,250,0.4)] hover:bg-[rgba(255,255,255,0.02)]",
      )}
    >
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-3.5 rounded-r-sm bg-[rgba(255,255,250,0.5)]" />
      )}
      <Icon className="w-[18px] h-[18px]" strokeWidth={1.5} />
    </div>
  );
}

export function IconSidebar() {
  return (
    <div className="w-14 bg-raised border-r border-border-subtle flex flex-col items-center py-4 gap-1 shrink-0">
      {/* Logo */}
      <div className="w-8 h-8 bg-[rgba(255,255,250,0.08)] rounded-lg grid place-items-center mb-6">
        <Mic className="w-4 h-4 text-[rgba(255,255,250,0.8)]" strokeWidth={1.5} />
      </div>

      {/* Nav items */}
      <NavItem icon={LayoutGrid} label="会议" active />
      <NavItem icon={Settings} />

      <div className="flex-1" />

      {/* Avatar */}
      <div className="w-7 h-7 rounded-full bg-surface grid place-items-center text-[11px] font-semibold text-text-secondary cursor-pointer">
        U
      </div>
    </div>
  );
}
