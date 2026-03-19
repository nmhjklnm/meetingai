import { meetingsApi } from "../api/meetings";

export function useExport(meetingId: string) {
  const download = (format: "srt" | "txt" | "summary") => {
    const url = meetingsApi.exportUrl(meetingId, format);
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    a.click();
  };
  return { download };
}
