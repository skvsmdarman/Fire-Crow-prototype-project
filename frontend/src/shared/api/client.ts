import { APIError } from "./errors";
import { clearStoredAuthSession } from "../../lib/authSession";
import { buildApiUrl } from "./baseUrl";

export { API_BASE_URL } from "./baseUrl";

interface FetchOptions extends RequestInit {
  params?: Record<string, string>;
}

export async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { params, headers, ...rest } = options;

  let url = buildApiUrl(path);
  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }

  const reqHeaders = new Headers(headers);
  // Include CSRF token for state‑changing requests (double‑submit cookie pattern).
  const method = (rest.method || "GET").toUpperCase();
  const unsafeMethods = ["POST", "PUT", "PATCH", "DELETE"]; // safe methods already exempted
  if (unsafeMethods.includes(method) && !reqHeaders.has("X-CSRF-Token")) {
    // Retrieve the csrf cookie (it is not HttpOnly after our server change).
    const csrfCookie = document.cookie
      .split("; ")
      .find((c) => c.startsWith("fc_csrf_token="));
    if (csrfCookie) {
      const token = csrfCookie.split("=")[1];
      reqHeaders.set("X-CSRF-Token", token);
    }
  }

  reqHeaders.set("Content-Type", "application/json");

  // Auth is handled by the HttpOnly session cookie (set by the backend).
  // No Authorization header needed — the cookie is sent via credentials: "include".

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      credentials: rest.credentials ?? "include",
      headers: reqHeaders,
    });
  } catch {
    throw new APIError("Network connection failed. Please verify your connection.");
  }

  const requestId = response.headers.get("X-Request-ID") || undefined;

  // Let 401 pass through here so the page can handle invalid credentials
  if ((response.status === 401 || response.status === 403) && typeof window !== "undefined" && !window.location.pathname.startsWith("/signin")) {
    clearStoredAuthSession();
    const searchParamsString = window.location.search;
    window.location.replace(`/signin${searchParamsString}`);
    throw new APIError("Session expired. Please sign in again.", response.status, undefined, requestId);
  }

  let data: unknown;
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      data = await response.text();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const errObj = data as Record<string, unknown> | null;
    const message = (errObj?.detail as string) || (errObj?.message as string) || `API request failed with status ${response.status}`;
    throw new APIError(message, response.status, errObj?.code as string, requestId);
  }

  return data as T;
}

export const apiClient = {
  get: <T>(path: string, options?: FetchOptions) => request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: FetchOptions) =>
    request<T>(path, { ...options, method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown, options?: FetchOptions) =>
    request<T>(path, { ...options, method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string, options?: FetchOptions) => request<T>(path, { ...options, method: "DELETE" }),
};
