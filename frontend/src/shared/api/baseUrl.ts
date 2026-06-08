const ABSOLUTE_URL_PATTERN = /^https?:\/\//i;

const trimTrailingSlash = (value: string): string => value.replace(/\/+$/, "");

export const isAbsoluteUrl = (value: string): boolean => ABSOLUTE_URL_PATTERN.test(value);

export const getApiBaseUrl = (): string => {
  const configured = trimTrailingSlash(process.env.NEXT_PUBLIC_API_URL?.trim() ?? "");
  if (configured) {
    return configured;
  }

  if (typeof window !== "undefined") {
    return `${window.location.origin}/api/v1`;
  }

  return "/api/v1";
};

export const API_BASE_URL = getApiBaseUrl();

export const buildApiUrl = (path: string): string => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
};
