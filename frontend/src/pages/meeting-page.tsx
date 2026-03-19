import { useParams } from "react-router-dom";
import { useMeetingList, useMeeting } from "../hooks/use-meetings";
import { DetailHeader } from "../components/meeting/detail-header";
import { RecordingManager } from "../components/meeting/recording-manager";
import { ProcessingView } from "../components/meeting/processing-view";

export function MeetingPage() {
  const { id } = useParams();
  const { data: meetings } = useMeetingList();
  const meetingId = id || meetings?.[0]?.id;
  const { data: meeting, isLoading } = useMeeting(meetingId);

  if (!meetingId || (!isLoading && !meetings?.length)) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-text-muted text-[13px]">还没有会议</div>
        </div>
      </div>
    );
  }

  if (!meeting || isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-text-muted text-[12px]">加载中...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <DetailHeader meeting={meeting} />
      <div className="flex-1 overflow-hidden">
        {meeting.status === "draft" && <RecordingManager meeting={meeting} />}
        {meeting.status === "processing" && (
          <ProcessingView meetingId={meeting.id} />
        )}
        {meeting.status === "done" && (
          <div className="p-6 text-text-muted">Meeting content (Task 10)</div>
        )}
        {meeting.status === "failed" && (
          <div className="flex-1 flex items-center justify-center text-center p-6">
            <div className="text-error">
              处理失败：{meeting.error_message}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
