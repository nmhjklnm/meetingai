import { useState, useCallback, useRef, useEffect } from "react";
import { Users, Check, X } from "lucide-react";
import { useUpdateSpeakers } from "../../hooks/use-meetings";
import type { Meeting, Speaker } from "../../types";

interface InlineEditProps {
  speaker: Speaker;
  onSave: (speaker_id: string, newName: string) => void;
  saving: boolean;
}

function InlineEdit({ speaker, onSave, saving }: InlineEditProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(speaker.name);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const handleSave = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && trimmed !== speaker.name) {
      onSave(speaker.speaker_id, trimmed);
    }
    setEditing(false);
  }, [value, speaker, onSave]);

  const handleCancel = useCallback(() => {
    setValue(speaker.name);
    setEditing(false);
  }, [speaker.name]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") handleSave();
      if (e.key === "Escape") handleCancel();
    },
    [handleSave, handleCancel],
  );

  if (editing) {
    return (
      <div className="flex items-center gap-1.5">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleSave}
          disabled={saving}
          className="bg-[rgba(255,255,255,0.03)] border border-border-focus rounded-sm px-2 py-1 text-[12px] text-text-primary outline-none w-32"
        />
        <button
          onClick={handleSave}
          disabled={saving}
          className="text-text-secondary hover:text-text-primary transition-colors p-0.5"
        >
          <Check size={12} />
        </button>
        <button
          onClick={handleCancel}
          className="text-text-muted hover:text-text-secondary transition-colors p-0.5"
        >
          <X size={12} />
        </button>
      </div>
    );
  }

  return (
    <span
      onClick={() => setEditing(true)}
      className="text-[12px] text-text-secondary cursor-pointer hover:text-text-primary transition-colors border-b border-dashed border-[rgba(255,255,250,0.1)] hover:border-[rgba(255,255,250,0.25)]"
    >
      {speaker.name}
    </span>
  );
}

interface SpeakerEditorProps {
  meeting: Meeting;
}

export function SpeakerEditor({ meeting }: SpeakerEditorProps) {
  const updateMutation = useUpdateSpeakers(meeting.id);

  const handleSave = useCallback(
    (speakerId: string, newName: string) => {
      const updated = meeting.speakers.map((s) =>
        s.speaker_id === speakerId ? { ...s, name: newName } : s,
      );
      updateMutation.mutate(updated);
    },
    [meeting.speakers, updateMutation],
  );

  if (!meeting.speakers.length) return null;

  return (
    <div className="mb-8">
      {/* Section title */}
      <div className="flex items-center gap-2 mb-3">
        <Users size={13} className="text-text-secondary" strokeWidth={1.5} />
        <span className="text-[11px] uppercase text-text-secondary font-medium tracking-[1px]">
          说话人
        </span>
      </div>

      <div className="space-y-2">
        {meeting.speakers.map((speaker) => (
          <div
            key={speaker.speaker_id}
            className="flex items-center gap-3 px-3 py-2 rounded-sm bg-[rgba(255,255,255,0.015)] border border-border-subtle"
          >
            <div className="w-6 h-6 rounded-full bg-[rgba(255,255,250,0.04)] border border-[rgba(255,255,250,0.06)] flex items-center justify-center text-[10px] font-semibold text-text-secondary shrink-0">
              {speaker.speaker_id.replace("SPEAKER_", "S")}
            </div>
            <InlineEdit
              speaker={speaker}
              onSave={handleSave}
              saving={updateMutation.isPending}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
