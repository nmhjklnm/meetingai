import { useEffect, useState, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createProgressWS } from "../api/client";
import type { Progress } from "../types";

const MAX_RECONNECT_DELAY = 10_000;

export function useProgress(meetingId: string | undefined, active: boolean) {
  const [progress, setProgress] = useState<Progress | null>(null);
  const qc = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const stoppedRef = useRef(false);

  const connect = useCallback(() => {
    if (!meetingId || stoppedRef.current) return;

    const ws = createProgressWS(meetingId);
    wsRef.current = ws;

    ws.onopen = () => {
      retriesRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        const data: Progress = JSON.parse(e.data);
        setProgress(data);
        if (data.status === "done" || data.status === "failed") {
          stoppedRef.current = true;
          qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
          qc.invalidateQueries({ queryKey: ["meetings"] });
          ws.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      if (stoppedRef.current) return;
      const delay = Math.min(1000 * 2 ** retriesRef.current, MAX_RECONNECT_DELAY);
      retriesRef.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, [meetingId, qc]);

  useEffect(() => {
    if (!meetingId || !active) return;

    stoppedRef.current = false;
    retriesRef.current = 0;
    connect();

    return () => {
      stoppedRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [meetingId, active, connect]);

  return progress;
}
