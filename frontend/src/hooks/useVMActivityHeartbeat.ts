import { useEffect, useRef } from "react";
import { vmsApi } from "@/api/vms";

/**
 * Reports keyboard/mouse/focus/console activity for idle-timeout detection
 * (see spec: Idle Detection). Debounced to at most once every 30s so it
 * doesn't spam the API on every keystroke.
 */
export function useVMActivityHeartbeat(sessionId: string | null) {
  const lastSent = useRef<number>(0);

  useEffect(() => {
    if (!sessionId) return;

    const report = () => {
      const now = Date.now();
      if (now - lastSent.current < 30_000) return;
      lastSent.current = now;
      vmsApi.reportActivity(sessionId).catch(() => {
        /* non-critical; next event will retry */
      });
    };

    window.addEventListener("keydown", report);
    window.addEventListener("mousemove", report);
    window.addEventListener("focus", report);

    return () => {
      window.removeEventListener("keydown", report);
      window.removeEventListener("mousemove", report);
      window.removeEventListener("focus", report);
    };
  }, [sessionId]);
}
