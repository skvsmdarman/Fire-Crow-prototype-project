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
    persistAuthSession(payload);
  }, []);

  const logout = useCallback(async () => {
    if (session.hasDashboardSession || session.hasConsoleSession || session.token) {
      try {
        await apiClient.post(ENDPOINTS.auth.logout);
      } catch (error) {
        console.warn("Logout request failed on server:", error);
      }
    }
    clearStoredAuthSession();
  }, [session.hasConsoleSession, session.hasDashboardSession, session.token]);

  const validateSession = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE_URL}${ENDPOINTS.auth.session}`, {
        credentials: "include",
      });
      if (!response.ok) {
        clearStoredAuthSession();
        return false;
      }
      const data = (await response.json()) as { user_id?: string; username?: string };
      if (!data.user_id || !data.username) {
        clearStoredAuthSession();
        return false;
      }
      persistAuthSession({
        user_id: data.user_id,
        username: data.username,
      });
      return true;
    } catch {
      clearStoredAuthSession();
      return false;
    }
  }, []);

  return {
    token: session.token,
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
