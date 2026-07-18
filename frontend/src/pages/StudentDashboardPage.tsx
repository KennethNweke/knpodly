import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Search, AlertTriangle, Wrench } from "lucide-react";
import { operatingSystemsApi } from "@/api/operatingSystems";
import { vmsApi } from "@/api/vms";
import OSCard from "@/components/os-catalogue/OSCard";
import OSCardSkeleton from "@/components/common/OSCardSkeleton";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { useVMActivityHeartbeat } from "@/hooks/useVMActivityHeartbeat";
import { useDashboardSocket, type DashboardEvent } from "@/hooks/useDashboardSocket";
import { useToast } from "@/context/ToastContext";
import { useAuth } from "@/context/AuthContext";

export default function StudentDashboardPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { user } = useAuth();

  const [search, setSearch] = useState("");
  const [familyFilter, setFamilyFilter] = useState<string>("all");
  const [confirmStopId, setConfirmStopId] = useState<string | null>(null);
  const [maintenanceMessage, setMaintenanceMessage] = useState<string | null>(null);

  const { data: operatingSystems = [], isLoading: osLoading } = useQuery({
    queryKey: ["operating-systems"],
    queryFn: operatingSystemsApi.list,
  });

  const { data: activeSession } = useQuery({
    queryKey: ["vms", "mine"],
    queryFn: vmsApi.getMine,
    refetchInterval: 5000, // fallback poll; the WS below pushes faster state transitions
  });

  useVMActivityHeartbeat(activeSession?.state === "running" ? activeSession.id : null);

  // Live push updates for expiry/idle warnings and maintenance mode — see
  // app/workers/scheduler.py (publishes vm.expiry_warning / vm.idle_warning)
  // and app/api/v1/routers/admin.py (publishes maintenance.enabled/disabled).
  useDashboardSocket((event: DashboardEvent) => {
    const belongsToMe = event.user_id === user?.id;
    switch (event.type) {
      case "vm.expiry_warning":
        if (belongsToMe) showToast("Your session expires soon. Extend it from the dashboard if you need more time.", "info");
        break;
      case "vm.idle_warning":
        if (belongsToMe) showToast("Your VM has been idle — it will shut down soon if you don't interact with it.", "info");
        break;
      case "vm.expired":
        if (belongsToMe) {
          showToast("Your session has expired and the VM was shut down.", "error");
          qc.invalidateQueries({ queryKey: ["vms", "mine"] });
        }
        break;
      case "vm.idle_timeout":
        if (belongsToMe) {
          showToast("Your VM was shut down due to inactivity.", "error");
          qc.invalidateQueries({ queryKey: ["vms", "mine"] });
        }
        break;
      case "vm.running":
        if (belongsToMe) qc.invalidateQueries({ queryKey: ["vms", "mine"] });
        break;
      case "vm.failed":
        if (belongsToMe) {
          showToast("Something went wrong launching your VM. Please try again.", "error");
          qc.invalidateQueries({ queryKey: ["vms", "mine"] });
        }
        break;
      case "maintenance.enabled":
        setMaintenanceMessage((event.message as string) ?? "The platform is under maintenance.");
        break;
      case "maintenance.disabled":
        setMaintenanceMessage(null);
        break;
    }
  });

  const launchMutation = useMutation({
    mutationFn: vmsApi.launch,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vms", "mine"] });
      showToast("VM launch requested — it'll be ready shortly.", "success");
    },
    onError: (err: any) => {
      showToast(err?.response?.data?.detail ?? "Could not launch VM.", "error");
    },
  });

  const stopMutation = useMutation({
    mutationFn: vmsApi.stop,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vms", "mine"] });
      showToast("VM stopped.", "success");
    },
  });

  const extendMutation = useMutation({
    mutationFn: vmsApi.extend,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vms", "mine"] });
      showToast("Session extended.", "success");
    },
    onError: (err: any) => {
      showToast(err?.response?.data?.detail ?? "Could not extend session.", "error");
    },
  });

  const families = useMemo(
    () => ["all", ...Array.from(new Set(operatingSystems.map((os) => os.family)))],
    [operatingSystems],
  );

  const filtered = operatingSystems.filter((os) => {
    const matchesSearch =
      !search || os.name.toLowerCase().includes(search.toLowerCase()) || os.family.toLowerCase().includes(search.toLowerCase());
    const matchesFamily = familyFilter === "all" || os.family === familyFilter;
    return matchesSearch && matchesFamily;
  });

  return (
    <div className="flex flex-col gap-6">
      {maintenanceMessage && (
        <div className="card p-4 flex items-start gap-3 border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
          <Wrench size={18} className="text-amber-600 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-amber-800 dark:text-amber-400">Maintenance mode</p>
            <p className="text-amber-700 dark:text-amber-500">{maintenanceMessage}</p>
          </div>
        </div>
      )}

      {activeSession?.expires_at && (
        <ExpiryBanner
          expiresAt={activeSession.expires_at}
          canExtend={activeSession.extension_count < activeSession.max_extensions}
          onExtend={() => extendMutation.mutate(activeSession.id)}
        />
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Welcome back</h1>
          <p className="text-gray-500 text-sm">Choose a distribution to launch your lab environment.</p>
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search distributions…"
              className="pl-8 pr-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent w-48"
            />
          </div>
          <select
            value={familyFilter}
            onChange={(e) => setFamilyFilter(e.target.value)}
            className="text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent px-2"
          >
            {families.map((f) => (
              <option key={f} value={f}>
                {f === "all" ? "All families" : f}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {osLoading
          ? Array.from({ length: 8 }).map((_, i) => <OSCardSkeleton key={i} />)
          : filtered.map((os) => (
              <OSCard
                key={os.id}
                os={os}
                activeSession={activeSession}
                launching={launchMutation.isPending}
                onLaunch={(slug) => launchMutation.mutate(slug)}
                onReconnect={(sessionId) => navigate(`/console/${sessionId}`)}
                onStop={(sessionId) => setConfirmStopId(sessionId)}
              />
            ))}
        {!osLoading && filtered.length === 0 && (
          <p className="col-span-full text-center text-gray-400 py-12">No distributions match your search.</p>
        )}
      </div>

      <ConfirmDialog
        open={!!confirmStopId}
        title="Stop this VM?"
        description="Your VM and everything on its disk will be destroyed immediately. This can't be undone."
        confirmLabel="Stop VM"
        destructive
        onCancel={() => setConfirmStopId(null)}
        onConfirm={() => {
          if (confirmStopId) stopMutation.mutate(confirmStopId);
          setConfirmStopId(null);
        }}
      />
    </div>
  );
}

function ExpiryBanner({
  expiresAt,
  canExtend,
  onExtend,
}: {
  expiresAt: string;
  canExtend: boolean;
  onExtend: () => void;
}) {
  const minutesLeft = Math.max(0, Math.round((new Date(expiresAt).getTime() - Date.now()) / 60000));
  if (minutesLeft > 15) return null;

  return (
    <div className="card p-4 flex items-center gap-3 border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
      <AlertTriangle size={18} className="text-amber-600 shrink-0" />
      <p className="text-sm flex-1 text-amber-800 dark:text-amber-400">
        Your session expires in about {minutesLeft} minute{minutesLeft === 1 ? "" : "s"}.
      </p>
      {canExtend && (
        <button onClick={onExtend} className="btn-secondary text-xs py-1.5">
          Extend session
        </button>
      )}
    </div>
  );
}
