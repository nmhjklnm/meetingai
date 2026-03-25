import { Mic, LayoutGrid, Settings, Sun, Moon } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { cn } from "../../lib/utils";
import { useTheme } from "../../contexts/theme";

interface NavItemProps {
  icon: typeof LayoutGrid;
  active?: boolean;
  onClick?: () => void;
}

function NavItem({ icon: Icon, active, onClick }: NavItemProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "relative w-10 h-10 rounded-md grid place-items-center cursor-pointer transition-all duration-[120ms]",
        active
          ? "bg-surface-active text-[rgb(var(--fg)_/_0.8)]"
          : "text-text-muted hover:text-text-secondary hover:bg-surface",
      )}
    >
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-3.5 rounded-r-sm bg-text-secondary" />
      )}
      <Icon className="w-[18px] h-[18px]" strokeWidth={1.5} />
    </div>
  );
}

export function IconSidebar() {
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const isSettings = location.pathname === "/settings";

  return (
    <div className="w-14 bg-raised border-r border-border-subtle flex flex-col items-center py-4 gap-1 shrink-0">
      {/* Logo */}
      <div className="w-8 h-8 bg-[rgb(var(--fg)_/_0.08)] rounded-lg grid place-items-center mb-6">
        <Mic className="w-4 h-4 text-[rgb(var(--fg)_/_0.8)]" strokeWidth={1.5} />
      </div>

      {/* Nav items */}
      <NavItem
        icon={LayoutGrid}
        active={!isSettings}
        onClick={() => navigate("/")}
      />
      <NavItem
        icon={Settings}
        active={isSettings}
        onClick={() => navigate("/settings")}
      />

      <div className="flex-1" />

      {/* Theme toggle */}
      <div
        onClick={toggle}
        className="w-10 h-10 rounded-md grid place-items-center cursor-pointer text-text-muted hover:text-text-secondary hover:bg-surface transition-all duration-[120ms]"
      >
        {theme === "dark" ? (
          <Sun className="w-[18px] h-[18px]" strokeWidth={1.5} />
        ) : (
          <Moon className="w-[18px] h-[18px]" strokeWidth={1.5} />
        )}
      </div>

      {/* Avatar */}
      <div className="w-7 h-7 rounded-full bg-surface grid place-items-center text-[11px] font-semibold text-text-secondary cursor-pointer">
        U
      </div>
    </div>
  );
}
