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
  if (!reqHeaders.has("Content-Type") && !(rest.body instanceof FormData)) {
    reqHeaders.set("Content-Type", "application/json");
  }

  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("fc_token");
    if (token) {
      reqHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

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

  if (response.status === 401 || response.status === 403) {
    if (typeof window !== "undefined") {
      clearStoredAuthSession();
      // Only redirect if we are not already on the sign-in page to prevent redirect loops
      if (!window.location.pathname.startsWith("/signin")) {
        const searchParamsString = window.location.search;
        window.location.replace(`/signin${searchParamsString}`);
      }
    }
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
