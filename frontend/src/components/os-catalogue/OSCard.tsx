import { Play, RotateCw, Square, Clock } from "lucide-react";
import type { OperatingSystem, VMSession } from "@/types";

interface OSCardProps {
  os: OperatingSystem;
  activeSession?: VMSession | null;
  onLaunch: (slug: string) => void;
  onReconnect: (sessionId: string) => void;
  onStop: (sessionId: string) => void;
  launching?: boolean;
}

/**
 * The core catalogue card described in the spec: icon, name, family,
 * package manager, architecture, description, status, and a launch/
 * reconnect/stop action depending on session state.
 */
export default function OSCard({ os, activeSession, onLaunch, onReconnect, onStop, launching }: OSCardProps) {
  const isComingSoon = os.status === "coming_soon";
  const isDisabled = os.status === "disabled";
  const isMine = activeSession?.operating_system_id === os.id;

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        {os.icon_path ? (
          <img src={`/vm-icons/${os.slug}`} alt={os.name} className="w-10 h-10 rounded-md object-contain" />
        ) : (
          <div className="w-10 h-10 rounded-md bg-primary-100 dark:bg-primary-900/40" />
        )}
        <div>
          <h3 className="font-semibold leading-tight">{os.name}</h3>
          <span className="text-xs text-gray-500">{os.architecture}</span>
        </div>
        <span
          className={`ml-auto text-xs px-2 py-0.5 rounded-full ${
            os.status === "available"
              ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
              : isComingSoon
                ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400"
                : "bg-gray-100 text-gray-500 dark:bg-gray-800"
          }`}
        >
          {os.status === "available" ? "Available" : isComingSoon ? "Coming Soon" : "Unavailable"}
        </span>
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">{os.description}</p>

      <dl className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-gray-500">
        <dt>Family</dt>
        <dd className="text-right">{os.family}</dd>
        <dt>Package Manager</dt>
        <dd className="text-right">{os.package_manager ?? "—"}</dd>
        <dt className="flex items-center gap-1"><Clock size={12} /> Est. Startup</dt>
        <dd className="text-right">{os.estimated_boot_secs}s</dd>
      </dl>

      <div className="mt-auto pt-2">
        {isComingSoon || isDisabled ? (
          <button disabled className="btn-secondary w-full opacity-50 cursor-not-allowed">
            {isComingSoon ? "Coming Soon" : "Unavailable"}
          </button>
        ) : isMine && activeSession ? (
          <div className="flex gap-2">
            <button onClick={() => onReconnect(activeSession.id)} className="btn-primary flex-1 gap-1">
              <RotateCw size={14} /> Reconnect
            </button>
            <button onClick={() => onStop(activeSession.id)} className="btn-secondary gap-1">
              <Square size={14} />
            </button>
          </div>
        ) : (
          <button
            onClick={() => onLaunch(os.slug)}
            disabled={launching || (!!activeSession && activeSession.operating_system_id !== os.id)}
            className="btn-primary w-full gap-1"
          >
            <Play size={14} /> Launch
          </button>
        )}
      </div>
    </div>
  );
}
