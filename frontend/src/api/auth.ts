import { apiClient } from "./client";
import type { User } from "@/types";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const authApi = {
  login: async (username: string, password: string): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>("/auth/login", { username, password });
    localStorage.setItem("knpodly_access_token", data.access_token);
    localStorage.setItem("knpodly_refresh_token", data.refresh_token);
    return data;
  },
  logout: () => {
    localStorage.removeItem("knpodly_access_token");
    localStorage.removeItem("knpodly_refresh_token");
  },
  hasToken: (): boolean => !!localStorage.getItem("knpodly_access_token"),
  me: () => apiClient.get<User>("/auth/me").then((r) => r.data),
};
