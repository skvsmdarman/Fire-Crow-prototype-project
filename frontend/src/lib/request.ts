import { clearSession } from "./auth-session";
import { buildApiUrl } from "./base-url";

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

function getCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const cookie = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith("fc_csrf_token="));
  return cookie ? cookie.split("=")[1] : null;
}

export async function request<T>(
  path: string,
  init: Omit<RequestInit, "body"> & { body?: unknown; params?: Record<string, string> } = {},
): Promise<T> {
  const { body, params, headers, method = "GET", ...rest } = init;
  const url = new URL(buildApiUrl(path));
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
  }

  const requestHeaders = new Headers(headers);
  const unsafe = ["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase());
  if (unsafe) {
    requestHeaders.set("Content-Type", "application/json");
    const csrf = getCsrfToken();
    if (csrf) {
      requestHeaders.set("X-CSRF-Token", csrf);
    }
  }

  const response = await fetch(url, {
    ...rest,
    method,
    credentials: "include",
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  }).catch(() => {
    throw new ApiError("Network connection failed.");
  });

  if ((response.status === 401 || response.status === 403) && typeof window !== "undefined") {
    clearSession();
    if (!window.location.pathname.startsWith("/signin")) {
      window.location.replace("/signin");
    }
    throw new ApiError("Session expired. Please sign in again.", response.status);
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json().catch(() => null) : await response.text().catch(() => null);
  if (!response.ok) {
    const message =
      (payload as { detail?: string; message?: string } | null)?.detail ??
      (payload as { detail?: string; message?: string } | null)?.message ??
      `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return payload as T;
}
