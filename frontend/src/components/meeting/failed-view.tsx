import { useState } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "../ui/button";
import { useStartProcessing } from "../../hooks/use-meetings";
import { useSettings } from "../../contexts/settings";
import type { Meeting } from "../../types";

interface FailedViewProps {
  meeting: Meeting;
}

export function FailedView({ meeting }: FailedViewProps) {
  const startMutation = useStartProcessing(meeting.id);
  const { settings } = useSettings();
  const [expanded, setExpanded] = useState(false);

  const errorMessage = meeting.error_message || "未知错误";

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="flex flex-col items-center gap-4 max-w-[400px] text-center">
        <AlertCircle
          size={48}
          className="text-error opacity-60"
          strokeWidth={1.2}
        />

        <h2 className="text-[17px] font-medium text-text-primary">
          处理失败
        </h2>

        <div
          onClick={() => setExpanded(!expanded)}
          className={`text-[12px] text-text-secondary cursor-pointer transition-all ${
            expanded ? "" : "line-clamp-3"
          }`}
        >
          {errorMessage}
        </div>

        <Button
          variant="primary"
          onClick={() => startMutation.mutate({
            chat_model: settings.chatModel,
            transcription_model: settings.transcriptionModel,
            ...(settings.apiKey ? { api_key: settings.apiKey } : {}),
            ...(settings.baseUrl ? { base_url: settings.baseUrl } : {}),
          })}
          disabled={startMutation.isPending}
          className="mt-2"
        >
          {startMutation.isPending ? "正在重试..." : "重试"}
        </Button>
      </div>
    </div>
  );
}
