import { AlertTriangle } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Blocking confirmation modal for destructive/irreversible actions (force
 * stop a VM, disable a user, etc). Renders nothing when `open` is false so
 * callers can keep it mounted at the page level and just toggle `open`.
 */
export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4" role="dialog" aria-modal="true">
      <div className="card w-full max-w-sm p-6 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          {destructive && (
            <div className="shrink-0 w-9 h-9 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <AlertTriangle size={18} className="text-red-600" />
            </div>
          )}
          <h2 className="font-semibold">{title}</h2>
        </div>
        <p className="text-sm text-gray-500">{description}</p>
        <div className="flex justify-end gap-2 mt-2">
          <button onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={destructive ? "btn-primary bg-red-600 hover:bg-red-700" : "btn-primary"}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
