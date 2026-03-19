import { Check } from "lucide-react";
import { useProgress } from "../../hooks/use-progress";

const STEPS = ["merge", "vad", "diarization", "transcription", "nlp", "save"];

const STEP_LABELS: Record<string, string> = {
  merge: "合并",
  vad: "检测",
  diarization: "识别",
  transcription: "转写",
  nlp: "摘要",
  save: "完成",
};

const STEP_DESCRIPTIONS: Record<string, string> = {
  merge: "正在合并录音文件",
  vad: "正在检测语音活动",
  diarization: "正在识别说话人",
  transcription: "正在转写语音",
  nlp: "正在生成智能摘要",
  save: "正在保存结果",
};

function formatEta(seconds: number): string {
  if (seconds > 60) {
    return `${Math.ceil(seconds / 60)} 分钟`;
  }
  return `${Math.ceil(seconds)} 秒`;
}

type StepState = "done" | "current" | "pending";

function getStepState(stepIndex: number, currentStep: number): StepState {
  if (stepIndex < currentStep) return "done";
  if (stepIndex === currentStep) return "current";
  return "pending";
}

interface StepCircleProps {
  index: number;
  state: StepState;
}

function StepCircle({ index, state }: StepCircleProps) {
  if (state === "done") {
    return (
      <div className="w-6 h-6 rounded-full flex items-center justify-center bg-[rgba(255,255,250,0.06)] border border-[rgba(255,255,250,0.1)]">
        <Check size={12} className="text-[rgba(255,255,250,0.6)]" />
      </div>
    );
  }

  if (state === "current") {
    return (
      <div className="w-6 h-6 rounded-full flex items-center justify-center bg-[rgba(255,255,250,0.06)] border border-[rgba(255,255,250,0.15)] shadow-[0_0_8px_rgba(255,255,250,0.1)]">
        <span className="text-[11px] font-medium text-[rgba(255,255,250,0.7)]">
          {index + 1}
        </span>
      </div>
    );
  }

  return (
    <div className="w-6 h-6 rounded-full flex items-center justify-center bg-surface border border-border-subtle">
      <span className="text-[11px] text-text-muted">{index + 1}</span>
    </div>
  );
}

interface ConnectorProps {
  leftState: StepState;
  rightState: StepState;
}

function Connector({ leftState, rightState }: ConnectorProps) {
  let className = "w-4 h-[1px] flex-shrink-0 ";

  if (leftState === "done" && rightState === "done") {
    className += "bg-[rgba(255,255,250,0.15)]";
  } else if (leftState === "done" && rightState === "current") {
    className +=
      "bg-gradient-to-r from-[rgba(255,255,250,0.15)] to-[rgba(255,255,250,0.06)]";
  } else {
    className += "bg-border-subtle";
  }

  return <div className={className} />;
}

interface ProcessingViewProps {
  meetingId: string;
}

export function ProcessingView({ meetingId }: ProcessingViewProps) {
  const progress = useProgress(meetingId, true);

  // WS not connected yet
  if (!progress) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-text-muted text-[13px]">等待连接...</div>
      </div>
    );
  }

  // step is 1-indexed from backend, convert to 0-indexed
  const currentStepIndex = Math.max(0, progress.step - 1);
  const currentStepName =
    progress.step_name || STEPS[currentStepIndex] || "merge";

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-[540px] space-y-8">
        {/* Step track */}
        <div className="flex items-center justify-center">
          {STEPS.map((step, i) => {
            const state = getStepState(i, currentStepIndex);
            return (
              <div key={step} className="flex items-center">
                <div className="flex flex-col items-center gap-1.5">
                  <StepCircle index={i} state={state} />
                  <span
                    className={`text-[10px] ${
                      state === "current"
                        ? "text-[rgba(255,255,250,0.7)]"
                        : state === "done"
                          ? "text-[rgba(255,255,250,0.4)]"
                          : "text-text-muted"
                    }`}
                  >
                    {STEP_LABELS[step]}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <Connector
                    leftState={state}
                    rightState={getStepState(i + 1, currentStepIndex)}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Progress card */}
        <div className="bg-raised border border-border-subtle rounded-lg p-6 space-y-4">
          {/* Top row: description + percent */}
          <div className="flex items-baseline justify-between">
            <div className="text-[15px] font-medium text-text-primary">
              {STEP_DESCRIPTIONS[currentStepName] || "处理中"}
            </div>
            <div className="text-[20px] font-bold text-cream tabular-nums">
              {Math.round(progress.percent)}%
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full h-1 bg-surface rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[rgba(255,255,250,0.2)] to-[rgba(255,255,250,0.5)] transition-all duration-500 ease-out"
              style={{ width: `${Math.min(100, progress.percent)}%` }}
            />
          </div>

          {/* Meta */}
          <div className="flex justify-between text-[11px] text-text-muted">
            <span>
              {progress.sub_total != null && progress.sub_done != null
                ? `已处理 ${progress.sub_done} / ${progress.sub_total} 段`
                : "\u00A0"}
            </span>
            <span>
              {progress.eta_seconds != null && progress.eta_seconds > 0
                ? `预计还需约 ${formatEta(progress.eta_seconds)}`
                : "\u00A0"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
