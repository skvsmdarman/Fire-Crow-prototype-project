import { useCallback, useSyncExternalStore } from "react";
import {
  subscribeToAuthSession,
  getStoredAuthSessionSnapshot,
  getServerAuthSessionSnapshot,
  persistAuthSession,
  clearStoredAuthSession,
  AuthSessionPayload,
} from "../../lib/authSession";
import { apiClient } from "../api/client";
import { API_BASE_URL } from "../api/client";
import { ENDPOINTS } from "../api/endpoints";

export function useAuthSession() {
  const session = useSyncExternalStore(
    subscribeToAuthSession,
    getStoredAuthSessionSnapshot,
    getServerAuthSessionSnapshot
  );

  const login = useCallback((payload: AuthSessionPayload) => {
    // Only persist non-sensitive metadata. The access token is in an HttpOnly cookie.
    persistAuthSession({
      user_id: payload.user_id,
      username: payload.username,
    });
  }, []);

  const logout = useCallback(async () => {
    if (session.hasDashboardSession || session.hasConsoleSession) {
      try {
        await apiClient.post(ENDPOINTS.auth.logout);
      } catch (error) {
        console.warn("Logout request failed on server:", error);
      }
    }
    clearStoredAuthSession();
  }, [session.hasConsoleSession, session.hasDashboardSession]);

  const validateSession = useCallback(async (): Promise<"valid" | "invalid" | "network_error"> => {
    try {
      const response = await fetch(`${API_BASE_URL}${ENDPOINTS.auth.session}`, {
        credentials: "include",
      });
      if (response.status === 401 || response.status === 403) {
        clearStoredAuthSession();
        return "invalid";
      }
      if (!response.ok) {
        return "network_error";
      }
      const data = (await response.json()) as { user_id?: string; username?: string };
      if (!data.user_id || !data.username) {
        clearStoredAuthSession();
        return "invalid";
      }
      persistAuthSession({
        user_id: data.user_id,
        username: data.username,
      });
      return "valid";
    } catch {
      return "network_error";
    }
  }, []);

  return {
    userId: session.userId,
    username: session.username,
    workspace: session.workspace,
    hasConsoleSession: session.hasConsoleSession,
    hasDashboardSession: session.hasDashboardSession,
    login,
    logout,
    validateSession,
  };
}
