import { useParams, useNavigate } from "react-router-dom";
import { Mic } from "lucide-react";
import {
  useMeetingList,
  useMeeting,
  useCreateMeeting,
} from "../hooks/use-meetings";
import { Button } from "../components/ui/button";
import { DetailHeader } from "../components/meeting/detail-header";
import { RecordingManager } from "../components/meeting/recording-manager";
import { ProcessingView } from "../components/meeting/processing-view";
import { MeetingContent } from "../components/meeting/meeting-content";
import { FailedView } from "../components/meeting/failed-view";

export function MeetingPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: meetings } = useMeetingList();
  const createMeeting = useCreateMeeting();
  const meetingId = id || meetings?.[0]?.id;
  const { data: meeting, isLoading } = useMeeting(meetingId);

  const handleCreate = async () => {
    const result = await createMeeting.mutateAsync("未命名会议");
    navigate(`/meetings/${result.id}`);
  };

  if (!meetingId || (!isLoading && !meetings?.length)) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Mic
            size={48}
            className="text-text-muted opacity-40"
            strokeWidth={1}
          />
          <div className="text-text-muted text-[13px]">还没有会议</div>
          <Button
            variant="primary"
            onClick={handleCreate}
            disabled={createMeeting.isPending}
          >
            {createMeeting.isPending ? "创建中..." : "创建第一个会议"}
          </Button>
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
      <div className="flex-1 overflow-hidden flex flex-col">
        {meeting.status === "draft" && <RecordingManager meeting={meeting} />}
        {meeting.status === "processing" && (
          <ProcessingView meetingId={meeting.id} />
        )}
        {meeting.status === "done" && <MeetingContent meeting={meeting} />}
        {meeting.status === "failed" && <FailedView meeting={meeting} />}
      </div>
    </div>
  );
}
