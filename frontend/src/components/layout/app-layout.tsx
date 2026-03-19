import { Outlet, useNavigate, useParams } from "react-router-dom";
import { useMeetingList, useCreateMeeting } from "../../hooks/use-meetings";
import { IconSidebar } from "./icon-sidebar";
import { MeetingList } from "./meeting-list";

export function AppLayout() {
  const { data: meetings = [] } = useMeetingList();
  const { id } = useParams();
  const navigate = useNavigate();
  const createMeeting = useCreateMeeting();

  const handleCreate = async () => {
    const result = await createMeeting.mutateAsync("未命名会议");
    navigate(`/meetings/${result.id}`);
  };

  return (
    <div className="flex h-screen bg-base">
      <IconSidebar />
      <MeetingList
        meetings={meetings}
        selectedId={id || meetings[0]?.id}
        onSelect={(mid) => navigate(`/meetings/${mid}`)}
        onCreate={handleCreate}
      />
      <main className="flex-1 flex flex-col min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
