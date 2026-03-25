import { Outlet, useNavigate, useParams, useLocation } from "react-router-dom";
import {
  useMeetingList,
  useCreateMeeting,
  useDeleteMeeting,
} from "../../hooks/use-meetings";
import { IconSidebar } from "./icon-sidebar";
import { MeetingList } from "./meeting-list";

export function AppLayout() {
  const { data: meetings = [] } = useMeetingList();
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const createMeeting = useCreateMeeting();
  const deleteMeeting = useDeleteMeeting();
  const isSettings = location.pathname === "/settings";

  const handleCreate = async () => {
    const result = await createMeeting.mutateAsync("未命名会议");
    navigate(`/meetings/${result.id}`);
  };

  const handleDelete = (meetingId: string) => {
    deleteMeeting.mutate(meetingId, {
      onSuccess: () => {
        if (meetingId === (id || meetings[0]?.id)) {
          const remaining = meetings.filter((m) => m.id !== meetingId);
          navigate(remaining.length ? `/meetings/${remaining[0].id}` : "/");
        }
      },
    });
  };

  return (
    <div className="flex h-screen bg-base">
      <IconSidebar />
      {!isSettings && (
        <MeetingList
          meetings={meetings}
          selectedId={id || meetings[0]?.id}
          onSelect={(mid) => navigate(`/meetings/${mid}`)}
          onCreate={handleCreate}
          onDelete={handleDelete}
        />
      )}
      <main className="flex-1 flex flex-col min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
