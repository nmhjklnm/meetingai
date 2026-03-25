import { Search } from "lucide-react";
import { cn } from "../../lib/utils";

interface SearchInputProps {
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function SearchInput({
  placeholder = "搜索",
  value,
  onChange,
  className,
}: SearchInputProps) {
  return (
    <div
      className={cn(
        "bg-surface border border-border-subtle rounded-sm px-3 py-1.5 flex items-center gap-2 text-[12px] text-text-muted focus-within:border-border-focus transition-colors",
        className,
      )}
    >
      <Search className="w-3.5 h-3.5 shrink-0" strokeWidth={1.5} />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="bg-transparent outline-none w-full text-text-secondary placeholder:text-text-muted"
      />
    </div>
  );
}
