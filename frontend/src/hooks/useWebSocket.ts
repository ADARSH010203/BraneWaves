/* ─── ARC Platform — useWebSocket Hook ────────────────────────────── */
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { WSEvent } from "@/types";
import { getAccessToken } from "@/lib/auth";
import { TaskWebSocket } from "@/lib/ws";

export function useWebSocket(taskId: string | null) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [latestEvent, setLatestEvent] = useState<WSEvent | null>(null);
  const wsRef = useRef<TaskWebSocket | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const token = getAccessToken();
    if (!token) return;

    const ws = new TaskWebSocket(taskId, token);
    wsRef.current = ws;

    const unsub = ws.onEvent((event) => {
      if (event.event === "connected") {
        setConnected(true);
      } else {
        setEvents((prev) => [...prev, event]);
        setLatestEvent(event);
      }
    });

    ws.connect();

    return () => {
      unsub();
      ws.disconnect();
    };
  }, [taskId]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setLatestEvent(null);
  }, []);

  return { events, connected, latestEvent, clearEvents };
}
