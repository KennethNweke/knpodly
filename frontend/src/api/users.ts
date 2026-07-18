import { apiClient } from "./client";
import type { User, UserRole } from "@/types";

export const usersApi = {
  list: (role?: UserRole) => apiClient.get<User[]>("/users", { params: role ? { role } : {} }).then((r) => r.data),
  create: (payload: { username: string; full_name: string; email?: string; password: string; role: UserRole }) =>
    apiClient.post<User>("/users", payload).then((r) => r.data),
  resetPassword: (userId: string, newPassword: string) =>
    apiClient.post(`/users/${userId}/reset-password`, null, { params: { new_password: newPassword } }),
  disable: (userId: string) => apiClient.post(`/users/${userId}/disable`),
  enable: (userId: string) => apiClient.post(`/users/${userId}/enable`),
};
