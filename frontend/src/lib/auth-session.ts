export interface SessionIdentity {
  userId: string | null;
  username: string | null;
  workspace: string | null;
}

const AUTH_EVENT = "firecrow-auth-session";
const STORAGE_KEYS = {
  userId: "fc_user_id",
  username: "fc_username",
  workspace: "fc_workspace",
} as const;

function readStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}

export function getSessionIdentity(): SessionIdentity {
  const username = readStorage(STORAGE_KEYS.username);
  const workspace = readStorage(STORAGE_KEYS.workspace) ?? username;
  return {
    userId: readStorage(STORAGE_KEYS.userId),
    username,
    workspace,
  };
}

export function persistSession(payload: { user_id: string; username: string }): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEYS.userId, payload.user_id);
  window.localStorage.setItem(STORAGE_KEYS.username, payload.username);
  window.localStorage.setItem(STORAGE_KEYS.workspace, payload.username);
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function clearSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  Object.values(STORAGE_KEYS).forEach((key) => window.localStorage.removeItem(key));
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function subscribeToSession(callback: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handler = () => callback();
  window.addEventListener("storage", handler);
  window.addEventListener(AUTH_EVENT, handler);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener(AUTH_EVENT, handler);
  };
}
