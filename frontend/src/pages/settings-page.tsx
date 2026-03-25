import { Sun, Moon, ChevronDown, Eye, EyeOff } from "lucide-react";
import { useTheme } from "../contexts/theme";
import { useSettings } from "../contexts/settings";
import { useState, useRef, useEffect } from "react";

const CHAT_MODELS = [
  { value: "gpt-4o", label: "GPT-4o", desc: "速度与质量均衡" },
  { value: "gpt-4o-mini", label: "GPT-4o Mini", desc: "更快、更便宜" },
  { value: "gpt-4.1", label: "GPT-4.1", desc: "最新旗舰模型" },
  { value: "gpt-4.1-mini", label: "GPT-4.1 Mini", desc: "轻量旗舰" },
  { value: "gpt-4.1-nano", label: "GPT-4.1 Nano", desc: "极速经济" },
];

const TRANSCRIPTION_MODELS = [
  { value: "gpt-4o-transcribe", label: "GPT-4o Transcribe", desc: "高精度转录" },
  { value: "gpt-4o-mini-transcribe", label: "GPT-4o Mini Transcribe", desc: "更快、更便宜" },
  { value: "whisper-1", label: "Whisper-1", desc: "经典 Whisper 模型" },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="text-[11px] uppercase text-text-muted font-medium tracking-[1px]">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Dropdown({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string; desc?: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const current = options.find((o) => o.value === value) || { label: value };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2.5 bg-surface border border-border-subtle rounded-sm text-[13px] text-text-primary hover:bg-surface-hover transition-colors"
      >
        <span>{current.label}</span>
        <ChevronDown size={14} className="text-text-muted" />
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full mt-1 bg-raised border border-border-subtle rounded-sm shadow-lg z-50 py-1 max-h-60 overflow-y-auto">
          {options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => { onChange(opt.value); setOpen(false); }}
              className={`w-full text-left px-3 py-2 hover:bg-surface-hover transition-colors ${
                opt.value === value ? "text-cream" : "text-text-secondary"
              }`}
            >
              <div className="text-[13px]">{opt.label}</div>
              {opt.desc && (
                <div className="text-[11px] text-text-muted mt-0.5">{opt.desc}</div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SecretInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="flex items-center gap-2 bg-surface border border-border-subtle rounded-sm px-3 py-2 focus-within:border-border-focus transition-colors">
      <input
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 bg-transparent outline-none text-[13px] text-text-primary placeholder:text-text-muted"
      />
      <button
        onClick={() => setVisible(!visible)}
        className="text-text-muted hover:text-text-secondary transition-colors shrink-0"
        type="button"
      >
        {visible ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    </div>
  );
}

export function SettingsPage() {
  const { theme, toggle } = useTheme();
  const { settings, update } = useSettings();

  return (
    <div className="flex-1 flex flex-col">
      <div className="px-6 py-3 border-b border-border-subtle min-h-[56px] flex items-center">
        <h1 className="text-[17px] font-medium text-text-primary tracking-tight">
          设置
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-[480px] space-y-8">
          {/* Theme */}
          <Section title="外观">
            <div className="flex gap-3">
              <button
                onClick={() => theme !== "dark" && toggle()}
                className={`flex-1 flex items-center gap-3 px-4 py-3 rounded-sm border transition-colors ${
                  theme === "dark"
                    ? "border-border-focus bg-surface-active text-cream"
                    : "border-border-subtle bg-surface text-text-secondary hover:bg-surface-hover"
                }`}
              >
                <Moon size={16} />
                <span className="text-[13px] font-medium">深色</span>
              </button>
              <button
                onClick={() => theme !== "light" && toggle()}
                className={`flex-1 flex items-center gap-3 px-4 py-3 rounded-sm border transition-colors ${
                  theme === "light"
                    ? "border-border-focus bg-surface-active text-cream"
                    : "border-border-subtle bg-surface text-text-secondary hover:bg-surface-hover"
                }`}
              >
                <Sun size={16} />
                <span className="text-[13px] font-medium">浅色</span>
              </button>
            </div>
          </Section>

          {/* API Config */}
          <Section title="API 配置">
            <div className="space-y-3">
              <div>
                <label className="text-[12px] text-text-secondary block mb-1.5">Base URL</label>
                <input
                  type="text"
                  value={settings.baseUrl}
                  onChange={(e) => update({ baseUrl: e.target.value })}
                  placeholder="留空使用服务端默认值"
                  className="w-full bg-surface border border-border-subtle rounded-sm px-3 py-2 text-[13px] text-text-primary placeholder:text-text-muted outline-none focus:border-border-focus transition-colors"
                />
              </div>
              <div>
                <label className="text-[12px] text-text-secondary block mb-1.5">API Key</label>
                <SecretInput
                  value={settings.apiKey}
                  onChange={(v) => update({ apiKey: v })}
                  placeholder="留空使用服务端默认值"
                />
              </div>
              <p className="text-[11px] text-text-muted leading-relaxed">
                覆盖服务端 .env 中的配置。留空则使用服务端默认值。支持 OpenAI 兼容接口。
              </p>
            </div>
          </Section>

          {/* Transcription Model */}
          <Section title="转录模型">
            <Dropdown
              options={TRANSCRIPTION_MODELS}
              value={settings.transcriptionModel}
              onChange={(v) => update({ transcriptionModel: v })}
            />
            <p className="text-[11px] text-text-muted leading-relaxed">
              用于语音转文字的模型。
            </p>
          </Section>

          {/* Chat Model */}
          <Section title="摘要模型">
            <Dropdown
              options={CHAT_MODELS}
              value={settings.chatModel}
              onChange={(v) => update({ chatModel: v })}
            />
            <p className="text-[11px] text-text-muted leading-relaxed">
              用于生成会议摘要、关键词和行动项的模型。
            </p>
          </Section>
        </div>
      </div>
    </div>
  );
}
