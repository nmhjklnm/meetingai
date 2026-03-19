import { useEffect, useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createProgressWS } from "../api/client";
import type { Progress } from "../types";

export function useProgress(meetingId: string | undefined, active: boolean) {
  const [progress, setProgress] = useState<Progress | null>(null);
  const qc = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!meetingId || !active) return;

    const ws = createProgressWS(meetingId);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const data: Progress = JSON.parse(e.data);
        setProgress(data);
        if (data.status === "done" || data.status === "failed") {
          qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
          qc.invalidateQueries({ queryKey: ["meetings"] });
          ws.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => ws.close();

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [meetingId, active, qc]);

  return progress;
}
