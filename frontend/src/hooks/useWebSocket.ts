/* ─── ARC Platform — useWebSocket Hook ────────────────────────────── */
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { WSEvent } from "@/types";
import { getAccessToken } from "@/lib/auth";
import { api } from "@/lib/api";
import { TaskWebSocket } from "@/lib/ws";

export function useWebSocket(taskId: string | null) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [latestEvent, setLatestEvent] = useState<WSEvent | null>(null);
  const wsRef = useRef<TaskWebSocket | null>(null);

  useEffect(() => {
    if (!taskId) return;

    let active = true;
    let cleanup: (() => void) | undefined;

    const connect = async () => {
      // Validate/refresh the short-lived access token before opening the socket.
      // api.getMe() uses the single-flight refresh-cookie path on a 401.
      try {
        await api.getMe();
      } catch {
        return;
      }
      if (!active) return;

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
      cleanup = () => {
        unsub();
        ws.disconnect();
      };
    };

    void connect();

    return () => {
      active = false;
      cleanup?.();
      wsRef.current = null;
      setConnected(false);
    };
  }, [taskId]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setLatestEvent(null);
  }, []);

  return { events, connected, latestEvent, clearEvents };
}
