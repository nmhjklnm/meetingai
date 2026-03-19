import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,
});

export function createProgressWS(meetingId: string): WebSocket {
  const wsBase = BASE_URL.startsWith("http")
    ? BASE_URL.replace(/^http/, "ws").replace(/\/api$/, "")
    : `ws://${window.location.host}`;
  return new WebSocket(`${wsBase}/ws/meetings/${meetingId}/progress`);
}
