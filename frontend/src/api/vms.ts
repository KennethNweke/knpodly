import { apiClient } from "./client";
import type { VMSession } from "@/types";

export const vmsApi = {
  launch: (osSlug: string) =>
    apiClient.post<VMSession>("/vms", { os_slug: osSlug }).then((r) => r.data),

  getMine: () => apiClient.get<VMSession | null>("/vms/mine").then((r) => r.data),

  listAll: () => apiClient.get<VMSession[]>("/vms").then((r) => r.data),

  stop: (sessionId: string) =>
    apiClient.post<VMSession>(`/vms/${sessionId}/stop`).then((r) => r.data),

  forceStop: (sessionId: string) =>
    apiClient.post<VMSession>(`/vms/${sessionId}/force-stop`).then((r) => r.data),

  extend: (sessionId: string) =>
    apiClient.post<VMSession>(`/vms/${sessionId}/extend`).then((r) => r.data),

  reportActivity: (sessionId: string) =>
    apiClient.post(`/vms/${sessionId}/activity`),
};
