import { TimelinePanel } from "./timeline-panel";
import { SummaryPanel } from "./summary-panel";
import { TranscriptPanel } from "./transcript-panel";
import { SpeakerEditor } from "./speaker-editor";
import type { Meeting } from "../../types";

interface MeetingContentProps {
  meeting: Meeting;
}

export function MeetingContent({ meeting }: MeetingContentProps) {
  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left panel: timeline + summary + speaker editor */}
      <div className="w-[46%] border-r border-border-subtle overflow-y-auto p-6">
        <SpeakerEditor meeting={meeting} />
        <TimelinePanel segments={meeting.segments} />
        <SummaryPanel summary={meeting.summary} />
      </div>

      {/* Right panel: transcript */}
      <div className="flex-1 overflow-y-auto p-6">
        <TranscriptPanel meeting={meeting} />
      </div>
    </div>
  );
}
