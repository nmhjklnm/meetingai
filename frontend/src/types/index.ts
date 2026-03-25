export type MeetingStatus = "draft" | "processing" | "done" | "failed";

export interface Recording {
  id: number;
  meeting_id: string;
  filename: string;
  file_size: number;
  duration: number | null;
  order: number;
  uploaded_at: string;
}

export interface MeetingListItem {
  id: string;
  title: string;
  status: MeetingStatus;
  recording_count: number;
  total_duration: number | null;
  num_speakers: number | null;
  created_at: string;
}

export interface Speaker {
  speaker_id: string;
  name: string;
}

export interface Segment {
  id: number;
  start: number;
  end: number;
  speaker_id: string;
  speaker_name: string;
  text: string | null;
}

export interface ActionItem {
  assignee: string;
  task: string;
  deadline?: string;
}

export interface TimelineEntry {
  time: number;
  title: string;
}

export interface Summary {
  summary?: string;
  timeline?: TimelineEntry[];
  speakers?: Record<string, string[]>;
  action_items?: ActionItem[];
  keywords?: string[];
  error?: string;
}

export interface Meeting {
  id: string;
  title: string;
  status: MeetingStatus;
  audio_duration: number | null;
  num_speakers: number | null;
  summary: Summary | null;
  error_message: string | null;
  created_at: string;
  recordings: Recording[];
  speakers: Speaker[];
  segments: Segment[];
}

export interface Progress {
  step: number;
  total_steps: number;
  step_name: string;
  percent: number;
  sub_done?: number;
  sub_total?: number;
  eta_seconds?: number;
  status: string;
}
