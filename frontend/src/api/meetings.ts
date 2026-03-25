import { api } from "./client";
import type { Meeting, MeetingListItem, Speaker } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

export const meetingsApi = {
  create(title: string): Promise<Meeting> {
    return api.post("/meetings", { title }).then((r) => r.data);
  },

  list(): Promise<MeetingListItem[]> {
    return api.get("/meetings").then((r) => r.data);
  },

  get(id: string): Promise<Meeting> {
    return api.get(`/meetings/${id}`).then((r) => r.data);
  },

  remove(id: string): Promise<void> {
    return api.delete(`/meetings/${id}`).then(() => undefined);
  },

  uploadRecording(meetingId: string, file: File): Promise<void> {
    const form = new FormData();
    form.append("file", file);
    return api
      .post(`/meetings/${meetingId}/recordings`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then(() => undefined);
  },

  removeRecording(meetingId: string, recordingId: number): Promise<void> {
    return api
      .delete(`/meetings/${meetingId}/recordings/${recordingId}`)
      .then(() => undefined);
  },

  updateTitle(meetingId: string, title: string): Promise<void> {
    return api.patch(`/meetings/${meetingId}`, { title }).then(() => undefined);
  },

  startProcessing(
    meetingId: string,
    opts?: {
      context?: string;
      chat_model?: string;
      transcription_model?: string;
      api_key?: string;
      base_url?: string;
    },
  ): Promise<void> {
    return api
      .post(`/meetings/${meetingId}/process`, opts || {})
      .then(() => undefined);
  },

  updateSpeakers(
    meetingId: string,
    speakers: Speaker[]
  ): Promise<void> {
    return api
      .patch(`/meetings/${meetingId}/speakers`, { speakers })
      .then(() => undefined);
  },

  exportUrl(meetingId: string, format: "srt" | "txt" | "summary"): string {
    return `${BASE_URL}/meetings/${meetingId}/export/${format}`;
  },
};
