import { Sun, Moon, ChevronDown, Eye, EyeOff, Loader2, CheckCircle, XCircle } from "lucide-react";
import { useTheme } from "../contexts/theme";
import { useSettings } from "../contexts/settings";
import { meetingsApi } from "../api/meetings";
import { useState, useRef, useEffect, useCallback } from "react";

// ── Model lists ─────────────────────────────────────────────────────────────

const CHAT_MODELS = [
  { value: "gpt-4o", label: "GPT-4o", desc: "速度与质量均衡" },
  { value: "gpt-4o-mini", label: "GPT-4o Mini", desc: "更快、更便宜" },
  { value: "gpt-4.1", label: "GPT-4.1", desc: "旗舰模型" },
  { value: "gpt-4.1-mini", label: "GPT-4.1 Mini", desc: "轻量旗舰" },
  { value: "gpt-4.1-nano", label: "GPT-4.1 Nano", desc: "极速经济" },
  { value: "gpt-4.5-preview", label: "GPT-4.5 Preview", desc: "预览版" },
  { value: "gpt-5.1", label: "GPT-5.1", desc: "新一代基础" },
  { value: "gpt-5.2", label: "GPT-5.2", desc: "新一代进阶" },
  { value: "gpt-5.3", label: "GPT-5.3", desc: "新一代高级" },
  { value: "gpt-5.4", label: "GPT-5.4", desc: "新一代旗舰" },
];

const TRANSCRIPTION_MODELS = [
  { value: "gpt-4o-transcribe", label: "GPT-4o Transcribe", desc: "高精度转录" },
  { value: "gpt-4o-mini-transcribe", label: "GPT-4o Mini Transcribe", desc: "更快、更便宜" },
  { value: "whisper-1", label: "Whisper-1", desc: "经典 Whisper 模型" },
];

const TABS = [
  { id: "general", label: "通用" },
  { id: "models", label: "模型" },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ── Shared components ───────────────────────────────────────────────────────

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

// ── Model selector with check ───────────────────────────────────────────────

type CheckState = "idle" | "checking" | "ok" | "fail";

function ModelSelector({
  options,
  value,
  onChange,
  apiKey,
  baseUrl,
}: {
  options: { value: string; label: string; desc?: string }[];
  value: string;
  onChange: (v: string) => void;
  apiKey?: string;
  baseUrl?: string;
}) {
  const [open, setOpen] = useState(false);
  const [checkState, setCheckState] = useState<CheckState>("idle");
  const [checkError, setCheckError] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const runCheck = useCallback(async (model: string): Promise<boolean> => {
    setCheckState("checking");
    setCheckError("");
    try {
      const res = await meetingsApi.checkModel(model, apiKey, baseUrl);
      if (res.available) { setCheckState("ok"); return true; }
      setCheckState("fail");
      setCheckError(res.error || "模型不可用");
      return false;
    } catch {
      setCheckState("fail");
      setCheckError("检测请求失败");
      return false;
    }
  }, [apiKey, baseUrl]);

  const handleCheck = useCallback(() => { runCheck(value); }, [runCheck, value]);

  const handleSelect = useCallback(
    async (newValue: string) => {
      setOpen(false);
      // Check first, only apply if available
      const ok = await runCheck(newValue);
      if (ok) onChange(newValue);
    },
    [runCheck, onChange],
  );

  const current = options.find((o) => o.value === value) || { label: value };

  return (
    <div className="space-y-2">
      <div className="flex gap-2" ref={ref}>
        {/* Dropdown */}
        <div className="relative flex-1">
          <button
            onClick={() => setOpen(!open)}
            disabled={checkState === "checking"}
            className="w-full flex items-center justify-between px-3 py-2.5 bg-surface border border-border-subtle rounded-sm text-[13px] text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-60"
          >
            <span className="flex items-center gap-2">
              {checkState === "checking" && <Loader2 size={13} className="animate-spin text-text-muted" />}
              {current.label}
            </span>
            <ChevronDown size={14} className="text-text-muted" />
          </button>
          {open && (
            <div className="absolute left-0 right-0 top-full mt-1 bg-raised border border-border-subtle rounded-sm shadow-lg z-50 py-1 max-h-60 overflow-y-auto">
              {options.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleSelect(opt.value)}
                  className={`w-full text-left px-3 py-2 hover:bg-surface-hover transition-colors ${
                    opt.value === value ? "text-cream" : "text-text-secondary"
                  }`}
                >
                  <div className="text-[13px]">{opt.label}</div>
                  {opt.desc && <div className="text-[11px] text-text-muted mt-0.5">{opt.desc}</div>}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Check button */}
        <button
          onClick={handleCheck}
          disabled={checkState === "checking"}
          className="px-3 py-2.5 bg-surface border border-border-subtle rounded-sm text-[12px] text-text-secondary hover:bg-surface-hover transition-colors shrink-0 disabled:opacity-60"
        >
          {checkState === "checking" ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            "检测"
          )}
        </button>
      </div>

      {/* Status feedback */}
      {checkState === "ok" && (
        <div className="flex items-center gap-1.5 text-[11px] text-[rgb(80_200_120)]">
          <CheckCircle size={12} />
          <span>模型可用</span>
        </div>
      )}
      {checkState === "fail" && (
        <div className="flex items-center gap-1.5 text-[11px] text-error">
          <XCircle size={12} />
          <span>{checkError}</span>
        </div>
      )}
    </div>
  );
}

// ── Tab: General ────────────────────────────────────────────────────────────

function GeneralTab() {
  const { theme, toggle } = useTheme();
  const { settings, update } = useSettings();

  return (
    <div className="space-y-8">
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
    </div>
  );
}

// ── Tab: Models ─────────────────────────────────────────────────────────────

function ModelsTab() {
  const { settings, update } = useSettings();

  return (
    <div className="space-y-8">
      <Section title="转录模型">
        <ModelSelector
          options={TRANSCRIPTION_MODELS}
          value={settings.transcriptionModel}
          onChange={(v) => update({ transcriptionModel: v })}
          apiKey={settings.apiKey || undefined}
          baseUrl={settings.baseUrl || undefined}
        />
        <p className="text-[11px] text-text-muted leading-relaxed">
          用于语音转文字。切换后自动检测模型是否可用。
        </p>
      </Section>

      <Section title="摘要模型">
        <ModelSelector
          options={CHAT_MODELS}
          value={settings.chatModel}
          onChange={(v) => update({ chatModel: v })}
          apiKey={settings.apiKey || undefined}
          baseUrl={settings.baseUrl || undefined}
        />
        <p className="text-[11px] text-text-muted leading-relaxed">
          用于生成会议摘要、关键词和行动项。切换后自动检测模型是否可用。
        </p>
      </Section>
    </div>
  );
}

// ── Settings page ───────────────────────────────────────────────────────────

export function SettingsPage() {
  const [tab, setTab] = useState<TabId>("general");

  return (
    <div className="flex-1 flex flex-col">
      {/* Header + Tabs */}
      <div className="border-b border-border-subtle">
        <div className="px-6 pt-3 pb-0">
          <h1 className="text-[17px] font-medium text-text-primary tracking-tight mb-3">
            设置
          </h1>
          <div className="flex gap-0">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-4 py-2 text-[13px] font-medium border-b-2 transition-colors ${
                  tab === t.id
                    ? "border-cream text-cream"
                    : "border-transparent text-text-muted hover:text-text-secondary"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-[480px]">
          {tab === "general" && <GeneralTab />}
          {tab === "models" && <ModelsTab />}
        </div>
      </div>
    </div>
  );
}
