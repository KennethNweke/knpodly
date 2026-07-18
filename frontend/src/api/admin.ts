import { apiClient } from "./client";
import type { AuditLogEntry, HostStats, MaintenanceStatus, VMLimitPolicy } from "@/types";

export const adminApi = {
  hostStats: () => apiClient.get<HostStats>("/admin/host-stats").then((r) => r.data),

  maintenanceStatus: () => apiClient.get<MaintenanceStatus>("/admin/maintenance").then((r) => r.data),
  enableMaintenance: (message: string) =>
    apiClient.post("/admin/maintenance/enable", null, { params: { message } }),
  disableMaintenance: () => apiClient.post("/admin/maintenance/disable"),

  getLimitPolicy: () => apiClient.get<VMLimitPolicy>("/admin/vm-limit-policy").then((r) => r.data),
  updateLimitPolicy: (updates: Partial<VMLimitPolicy>) =>
    apiClient.patch<VMLimitPolicy>("/admin/vm-limit-policy", updates).then((r) => r.data),

  auditLogs: (limit = 100) =>
    apiClient.get<AuditLogEntry[]>("/admin/audit-logs", { params: { limit } }).then((r) => r.data),
};
