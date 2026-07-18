import { useEffect, useRef, useState, type ReactNode } from "react";
// @novnc/novnc ships as a plain JS library with no official first-party
// TypeScript types; see src/types/novnc.d.ts for the minimal ambient
// declaration covering what this component uses.
import RFB from "@novnc/novnc";
import { AlertTriangle, Loader2 } from "lucide-react";

interface NoVNCViewerProps {
  consoleUrl: string;
}

type ConnectionState = "connecting" | "connected" | "disconnected" | "error";

/**
 * Wraps novnc-core's RFB client. `consoleUrl` is the per-session websocket
 * URL returned by the backend (wss://<host>/console/<token>) — the token
 * IS the authorization; RFB itself needs no separate credentials since the
 * VM's VNC server has no password (protected instead by the token + the
 * fact the socket is only reachable from the backend container, see
 * app/services/console_proxy.py).
 */
export default function NoVNCViewer({ consoleUrl }: NoVNCViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<RFB | null>(null);
  const [state, setState] = useState<ConnectionState>("connecting");

  useEffect(() => {
    if (!containerRef.current) return;
    setState("connecting");

    const rfb = new RFB(containerRef.current, consoleUrl, { wsProtocols: ["binary"] });
    rfb.scaleViewport = true;
    rfb.resizeSession = true;
    rfb.showDotCursor = true;

    const onConnect = () => setState("connected");
    const onDisconnect = () => setState("disconnected");
    const onCredentials = () => {
      // Student VMs are provisioned without a VNC password (see domain_xml.py);
      // this listener exists so a misconfigured deployment fails visibly
      // instead of hanging silently on a credentials prompt noVNC would
      // otherwise show inside the canvas.
      setState("error");
    };

    rfb.addEventListener("connect", onConnect);
    rfb.addEventListener("disconnect", onDisconnect);
    rfb.addEventListener("credentialsrequired", onCredentials);
    rfbRef.current = rfb;

    return () => {
      rfb.removeEventListener("connect", onConnect);
      rfb.removeEventListener("disconnect", onDisconnect);
      rfb.removeEventListener("credentialsrequired", onCredentials);
      rfb.disconnect();
      rfbRef.current = null;
    };
  }, [consoleUrl]);

  return (
    <div className="relative w-full h-full bg-black rounded-lg overflow-hidden">
      <div ref={containerRef} className="w-full h-full" />

      {state === "connecting" && (
        <Overlay>
          <Loader2 className="animate-spin" size={20} />
          <span>Connecting to console…</span>
        </Overlay>
      )}
      {state === "disconnected" && (
        <Overlay>
          <AlertTriangle size={20} />
          <span>Console disconnected. Reconnect from your dashboard if your VM is still running.</span>
        </Overlay>
      )}
      {state === "error" && (
        <Overlay>
          <AlertTriangle size={20} />
          <span>Unable to establish a console session. Contact your lecturer if this persists.</span>
        </Overlay>
      )}
    </div>
  );
}

function Overlay({ children }: { children: ReactNode }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/70 text-gray-200 text-sm">
      {children}
    </div>
  );
}
