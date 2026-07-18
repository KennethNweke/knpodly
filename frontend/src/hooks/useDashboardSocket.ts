import { useEffect, useRef } from "react";

export interface DashboardEvent {
  type: string;
  [key: string]: unknown;
}

/**
 * Opens the /ws/dashboard connection (backed by Redis pub/sub server-side,
 * see app/services/redis_bus.py) and forwards every event to `onEvent`.
 * Auto-reconnects with backoff on disconnect so a brief network blip or
 * backend restart doesn't leave the dashboard silently stale.
 */
export function useDashboardSocket(onEvent: (event: DashboardEvent) => void) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectDelay = 1000;
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const wsBase = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000/ws";

    const connect = () => {
      if (cancelled) return;
      socket = new WebSocket(`${wsBase}/dashboard`);

      socket.onmessage = (event) => {
        try {
          onEventRef.current(JSON.parse(event.data));
        } catch {
          // ignore malformed frames
        }
      };
      socket.onopen = () => {
        reconnectDelay = 1000;
      };
      socket.onclose = () => {
        if (cancelled) return;
        reconnectTimer = setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30_000);
      };
      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);
}
