import { useState, useEffect, useCallback, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { meetingsApi } from "../api/meetings";
import type { AppSettings } from "../contexts/settings";

export type RegenState = "idle" | "loading" | "done";

type ApiOpts = { chat_model?: string; api_key?: string; base_url?: string };

const POLL_INTERVAL = 1500;
const TIMEOUT = 60_000; // 1 minute timeout

function buildOpts(settings: AppSettings): ApiOpts {
  return {
    chat_model: settings.chatModel,
    ...(settings.apiKey ? { api_key: settings.apiKey } : {}),
    ...(settings.baseUrl ? { base_url: settings.baseUrl } : {}),
  };
}

/**
 * Generic hook for a regeneration task (timeline or summary).
 * Each uses its own Redis progress key (suffix) and API endpoint.
 * Includes a 60s timeout to prevent permanent loading state.
 */
export function useRegenerate(
  meetingId: string,
  settings: AppSettings,
  kind: "timeline" | "summary",
) {
  const qc = useQueryClient();
  const [state, setState] = useState<RegenState>("idle");
  const pollRef = useRef<ReturnType<typeof setInterval>>();
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const apiFn = kind === "timeline" ? meetingsApi.regenerateTimeline : meetingsApi.regenerateSummary;

  const mutation = useMutation({
    mutationFn: (opts: ApiOpts) => apiFn(meetingId, opts),
  });

  const cleanup = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = undefined; }
    if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = undefined; }
  }, []);

  // On mount: check backend progress
  useEffect(() => {
    let cancelled = false;
    meetingsApi.getProgress(meetingId, kind).then((p) => {
      if (cancelled) return;
      if (p.status === "processing") {
        setState("loading");
        startPolling();
      }
    });
    return () => { cancelled = true; cleanup(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId, kind]);

  const markDone = useCallback(async () => {
    cleanup();
    await qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
    setState("done");
    setTimeout(() => setState("idle"), 2500);
  }, [cleanup, qc, meetingId]);

  const startPolling = useCallback(() => {
    cleanup();

    // Timeout: force stop after 60s
    timeoutRef.current = setTimeout(() => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = undefined;
      // Try one final refresh anyway
      qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
      setState("idle");
    }, TIMEOUT);

    pollRef.current = setInterval(async () => {
      try {
        const p = await meetingsApi.getProgress(meetingId, kind);
        if (p.status !== "processing") {
          await markDone();
        }
      } catch {
        // network error — keep polling
      }
    }, POLL_INTERVAL);
  }, [meetingId, kind, qc, cleanup, markDone]);

  const trigger = useCallback(() => {
    setState("loading");
    mutation.mutate(buildOpts(settings), {
      onSuccess: () => startPolling(),
      onError: () => setState("idle"),
    });
  }, [mutation, settings, startPolling]);

  return { state, trigger };
}
