export interface AuthSessionPayload {
  access_token?: string;
  user_id: string;
  username: string;
}

export interface StoredAuthSession {
  userId: string | null;
  username: string | null;
  workspace: string | null;
  hasConsoleSession: boolean;
  hasDashboardSession: boolean;
}

const AUTH_SESSION_EVENT = "firecrow-auth-session";
const AUTH_STORAGE_KEYS = ["fc_user_id", "fc_username", "fc_workspace"] as const;
const EMPTY_SESSION: StoredAuthSession = {
  userId: null,
  username: null,
  workspace: null,
  hasConsoleSession: false,
  hasDashboardSession: false,
};

let cachedSessionSnapshot = EMPTY_SESSION;

function buildStoredAuthSession(): StoredAuthSession {
  if (typeof window === "undefined") {
    return EMPTY_SESSION;
  }

  const userId = window.localStorage.getItem("fc_user_id");
  const username = window.localStorage.getItem("fc_username") ?? window.localStorage.getItem("fc_workspace");
  const workspace = window.localStorage.getItem("fc_workspace") ?? username;

  return {
    userId,
    username,
    workspace,
    hasConsoleSession: Boolean(workspace),
    hasDashboardSession: Boolean(userId && username),
  };
}

function isSameSession(left: StoredAuthSession, right: StoredAuthSession): boolean {
  return (
    left.userId === right.userId &&
    left.username === right.username &&
    left.workspace === right.workspace &&
    left.hasConsoleSession === right.hasConsoleSession &&
    left.hasDashboardSession === right.hasDashboardSession
  );
}

function dispatchAuthSessionChange(): void {
  if (typeof window === "undefined") {
    return;
  }

  cachedSessionSnapshot = buildStoredAuthSession();
  window.dispatchEvent(new Event(AUTH_SESSION_EVENT));
}

export function getStoredAuthSessionSnapshot(): StoredAuthSession {
  const nextSnapshot = buildStoredAuthSession();
  if (isSameSession(cachedSessionSnapshot, nextSnapshot)) {
    return cachedSessionSnapshot;
  }

  cachedSessionSnapshot = nextSnapshot;
  return cachedSessionSnapshot;
}

export function getServerAuthSessionSnapshot(): StoredAuthSession {
  return EMPTY_SESSION;
}

export function getStoredAuthSession(): StoredAuthSession {
  return getStoredAuthSessionSnapshot();
}

export function subscribeToAuthSession(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const handleChange = () => {
    cachedSessionSnapshot = buildStoredAuthSession();
    onStoreChange();
  };

  window.addEventListener("storage", handleChange);
  window.addEventListener(AUTH_SESSION_EVENT, handleChange);

  return () => {
    window.removeEventListener("storage", handleChange);
    window.removeEventListener(AUTH_SESSION_EVENT, handleChange);
  };
}

export function persistAuthSession(session: AuthSessionPayload): void {
  if (typeof window === "undefined") {
    return;
  }

  // NOTE: The access token is stored in an HttpOnly cookie by the backend.
  // We deliberately do NOT persist it in localStorage to prevent XSS token theft.
  window.localStorage.setItem("fc_user_id", session.user_id);
  window.localStorage.setItem("fc_username", session.username);
  window.localStorage.setItem("fc_workspace", session.username);
  dispatchAuthSessionChange();
}

export function clearStoredAuthSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  for (const key of AUTH_STORAGE_KEYS) {
    window.localStorage.removeItem(key);
  }
  dispatchAuthSessionChange();
}
