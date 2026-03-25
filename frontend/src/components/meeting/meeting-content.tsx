import { TimelinePanel } from "./timeline-panel";
import { SummaryPanel } from "./summary-panel";
import { TranscriptPanel } from "./transcript-panel";
import { SpeakerEditor } from "./speaker-editor";
import { useRegenerate } from "../../hooks/use-regenerate";
import { useSettings } from "../../contexts/settings";
import type { Meeting } from "../../types";

interface MeetingContentProps {
  meeting: Meeting;
}

export function MeetingContent({ meeting }: MeetingContentProps) {
  const { settings } = useSettings();
  const timeline = useRegenerate(meeting.id, settings, "timeline");
  const summary = useRegenerate(meeting.id, settings, "summary");

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left panel */}
      <div className="w-[46%] border-r border-border-subtle overflow-y-auto p-6">
        <SpeakerEditor meeting={meeting} />
        <TimelinePanel
          summary={meeting.summary}
          segments={meeting.segments}
          regenState={timeline.state}
          onRegenerate={timeline.trigger}
        />
        <SummaryPanel
          summary={meeting.summary}
          regenState={summary.state}
          onRegenerate={summary.trigger}
        />
      </div>

      {/* Right panel */}
      <div className="flex-1 overflow-y-auto p-6">
        <TranscriptPanel meeting={meeting} />
      </div>
    </div>
  );
}
