import { useSyncExternalStore } from "react";
import {
  subscribeToAuthSession,
  getStoredAuthSessionSnapshot,
  getServerAuthSessionSnapshot,
  persistAuthSession,
  clearStoredAuthSession,
  AuthSessionPayload,
} from "../../lib/authSession";
import { apiClient } from "../api/client";
import { ENDPOINTS } from "../api/endpoints";

export function useAuthSession() {
  const session = useSyncExternalStore(
    subscribeToAuthSession,
    getStoredAuthSessionSnapshot,
    getServerAuthSessionSnapshot
  );

  const login = (payload: AuthSessionPayload) => {
    persistAuthSession(payload);
  };

  const logout = async () => {
    if (session.token) {
      try {
        await apiClient.post(ENDPOINTS.auth.logout);
      } catch (error) {
        console.warn("Logout request failed on server:", error);
      }
    }
    clearStoredAuthSession();
  };

  const validateSession = async (): Promise<boolean> => {
    if (!session.token) {
      clearStoredAuthSession();
      return false;
    }
    try {
      await apiClient.get(ENDPOINTS.auth.me);
      return true;
    } catch {
      clearStoredAuthSession();
      return false;
    }
  };

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
