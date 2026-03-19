import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { meetingsApi } from "../api/meetings";
import type { MeetingListItem } from "../types";

export function useMeetingList() {
  return useQuery({
    queryKey: ["meetings"],
    queryFn: meetingsApi.list,
    refetchInterval: (query) => {
      const data = query.state.data as MeetingListItem[] | undefined;
      if (data?.some((m) => m.status === "processing")) return 5000;
      return false;
    },
  });
}

export function useMeeting(id: string | undefined) {
  return useQuery({
    queryKey: ["meeting", id],
    queryFn: () => meetingsApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateMeeting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title: string) => meetingsApi.create(title),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["meetings"] }),
  });
}

export function useDeleteMeeting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => meetingsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["meetings"] }),
  });
}

export function useUploadRecording(meetingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => meetingsApi.uploadRecording(meetingId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
      qc.invalidateQueries({ queryKey: ["meetings"] });
    },
  });
}

export function useDeleteRecording(meetingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (recordingId: number) =>
      meetingsApi.removeRecording(meetingId, recordingId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
      qc.invalidateQueries({ queryKey: ["meetings"] });
    },
  });
}

export function useStartProcessing(meetingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (context?: string | void) =>
      meetingsApi.startProcessing(meetingId, context || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
      qc.invalidateQueries({ queryKey: ["meetings"] });
    },
  });
}

export function useUpdateSpeakers(meetingId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (speakers: { speaker_id: string; name: string }[]) =>
      meetingsApi.updateSpeakers(meetingId, speakers),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["meeting", meetingId] }),
  });
}
