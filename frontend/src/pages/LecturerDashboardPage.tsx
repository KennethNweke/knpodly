import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Wrench, ShieldAlert, Square } from "lucide-react";
import { adminApi } from "@/api/admin";
import { vmsApi } from "@/api/vms";
import { operatingSystemsApi } from "@/api/operatingSystems";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { useDashboardSocket, type DashboardEvent } from "@/hooks/useDashboardSocket";
import { useToast } from "@/context/ToastContext";

export default function LecturerDashboardPage() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [forceStopId, setForceStopId] = useState<string | null>(null);
  const [maintenanceMsg, setMaintenanceMsg] = useState("");

  const { data: hostStats } = useQuery({
    queryKey: ["admin", "host-stats"],
    queryFn: adminApi.hostStats,
    refetchInterval: 10000, // WS pushes handle fast-path updates; this is the slow-path fallback
  });

  const { data: vms = [] } = useQuery({
    queryKey: ["vms", "all"],
    queryFn: vmsApi.listAll,
    refetchInterval: 10000,
  });

  const { data: maintenance } = useQuery({
    queryKey: ["admin", "maintenance"],
    queryFn: adminApi.maintenanceStatus,
  });

  const { data: policy } = useQuery({
    queryKey: ["admin", "vm-limit-policy"],
    queryFn: adminApi.getLimitPolicy,
  });

  // Live updates: any vm.* event (launch/running/stopped/expired/idle) or a
  // catalogue resync invalidates the relevant query so the table/host stats
  // refresh immediately instead of waiting for the next poll.
  useDashboardSocket((event: DashboardEvent) => {
    if (String(event.type).startsWith("vm.")) {
      qc.invalidateQueries({ queryKey: ["vms", "all"] });
      qc.invalidateQueries({ queryKey: ["admin", "host-stats"] });
    }
    if (event.type === "maintenance.enabled" || event.type === "maintenance.disabled") {
      qc.invalidateQueries({ queryKey: ["admin", "maintenance"] });
    }
    if (event.type === "catalogue.resynced") {
      qc.invalidateQueries({ queryKey: ["operating-systems"] });
    }
  });

  const forceStopMutation = useMutation({
    mutationFn: vmsApi.forceStop,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vms", "all"] });
      showToast("VM force-stopped.", "success");
    },
  });

  const enableMaintenanceMutation = useMutation({
    mutationFn: adminApi.enableMaintenance,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "maintenance"] });
      showToast("Maintenance mode enabled.", "success");
      setMaintenanceMsg("");
    },
  });

  const disableMaintenanceMutation = useMutation({
    mutationFn: adminApi.disableMaintenance,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "maintenance"] });
      showToast("Maintenance mode disabled.", "success");
    },
  });

  const rescanMutation = useMutation({
    mutationFn: operatingSystemsApi.rescan,
    onSuccess: () => showToast("Catalogue rescan triggered.", "success"),
  });

  const updatePolicyMutation = useMutation({
    mutationFn: adminApi.updateLimitPolicy,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "vm-limit-policy"] });
      showToast("VM limits updated.", "success");
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">Lecturer Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Running VMs" value={hostStats?.running_vms ?? "—"} />
        <StatCard label="Queued" value={hostStats?.queued_vms ?? "—"} />
        <StatCard label="Host CPU" value={hostStats ? `${hostStats.host.cpu_count} cores` : "—"} />
        <StatCard label="Host Memory Free" value={hostStats ? `${hostStats.host.free_memory_mb} MB` : "—"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-4 flex flex-col gap-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Wrench size={16} /> Maintenance Mode
          </h2>
          {maintenance?.is_active ? (
            <>
              <p className="text-sm text-amber-600">
                Active: {maintenance.message}
              </p>
              <button
                onClick={() => disableMaintenanceMutation.mutate()}
                className="btn-secondary self-start"
              >
                Disable maintenance mode
              </button>
            </>
          ) : (
            <>
              <input
                value={maintenanceMsg}
                onChange={(e) => setMaintenanceMsg(e.target.value)}
                placeholder="Message shown to students…"
                className="rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-2 text-sm"
              />
              <button
                onClick={() => enableMaintenanceMutation.mutate(maintenanceMsg || "The platform is under maintenance.")}
                className="btn-secondary self-start"
              >
                Enable maintenance mode
              </button>
            </>
          )}
        </div>

        <div className="card p-4 flex flex-col gap-3">
          <h2 className="font-semibold flex items-center gap-2">
            <ShieldAlert size={16} /> VM Limits
          </h2>
          {policy && (
            <form
              className="grid grid-cols-2 gap-3 text-sm"
              onSubmit={(e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                updatePolicyMutation.mutate({
                  max_session_minutes: Number(fd.get("max_session_minutes")),
                  max_extension_minutes: Number(fd.get("max_extension_minutes")),
                  max_extensions: Number(fd.get("max_extensions")),
                  idle_warning_minutes: Number(fd.get("idle_warning_minutes")),
                  idle_timeout_minutes: Number(fd.get("idle_timeout_minutes")),
                  max_concurrent_vms_total: Number(fd.get("max_concurrent_vms_total")),
                });
              }}
            >
              <PolicyField name="max_session_minutes" label="Session (min)" defaultValue={policy.max_session_minutes} />
              <PolicyField name="max_extension_minutes" label="Extension (min)" defaultValue={policy.max_extension_minutes} />
              <PolicyField name="max_extensions" label="Max extensions" defaultValue={policy.max_extensions} />
              <PolicyField name="idle_warning_minutes" label="Idle warning (min)" defaultValue={policy.idle_warning_minutes} />
              <PolicyField name="idle_timeout_minutes" label="Idle timeout (min)" defaultValue={policy.idle_timeout_minutes} />
              <PolicyField name="max_concurrent_vms_total" label="Max concurrent VMs" defaultValue={policy.max_concurrent_vms_total} />
              <button type="submit" className="btn-primary col-span-2 mt-1">
                Save limits
              </button>
            </form>
          )}
        </div>
      </div>

      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Active Sessions</h2>
          <button onClick={() => rescanMutation.mutate()} className="btn-secondary text-xs py-1.5">
            Rescan catalogue
          </button>
        </div>
        <table className="w-full text-sm">
          <thead className="text-left text-gray-500 border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th className="py-2">Session</th>
              <th>State</th>
              <th>RAM</th>
              <th>vCPUs</th>
              <th>Expires</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {vms.map((vm) => (
              <tr key={vm.id} className="border-b border-gray-100 dark:border-gray-800/60">
                <td className="py-2 font-mono text-xs">{vm.id.slice(0, 8)}</td>
                <td>{vm.state}</td>
                <td>{vm.ram_mb} MB</td>
                <td>{vm.vcpus}</td>
                <td>{vm.expires_at ? new Date(vm.expires_at).toLocaleTimeString() : "—"}</td>
                <td>
                  {vm.state === "running" && (
                    <button
                      onClick={() => setForceStopId(vm.id)}
                      className="text-red-600 hover:text-red-700 flex items-center gap-1 text-xs"
                    >
                      <Square size={12} /> Force stop
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {vms.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-gray-400">
                  No active sessions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={!!forceStopId}
        title="Force-stop this VM?"
        description="This immediately destroys the student's VM and all unsaved work on it."
        confirmLabel="Force stop"
        destructive
        onCancel={() => setForceStopId(null)}
        onConfirm={() => {
          if (forceStopId) forceStopMutation.mutate(forceStopId);
          setForceStopId(null);
        }}
      />
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-2xl font-semibold mt-1">{value}</p>
    </div>
  );
}

function PolicyField({ name, label, defaultValue }: { name: string; label: string; defaultValue: number }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-gray-500">{label}</span>
      <input
        type="number"
        name={name}
        defaultValue={defaultValue}
        min={1}
        className="rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-sm"
      />
    </label>
  );
}
