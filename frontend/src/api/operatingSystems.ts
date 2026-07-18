import { apiClient } from "./client";
import type { OperatingSystem } from "@/types";

export const operatingSystemsApi = {
  list: () => apiClient.get<OperatingSystem[]>("/operating-systems").then((r) => r.data),
  rescan: () => apiClient.post("/operating-systems/rescan"),

  uploadImage: (slug: string, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post(`/operating-systems/${slug}/upload-image`, form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    });
  },

  uploadIcon: (slug: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post(`/operating-systems/${slug}/upload-icon`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};
