const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1"]);

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return trimTrailingSlash(configured);
  }

  if (typeof window !== "undefined") {
    const { protocol, hostname, port } = window.location;
    if (LOCAL_HOSTS.has(hostname) && port === "3000") {
      return "http://localhost:8000/api/v1";
    }
    return `${protocol}//${window.location.host}/api/v1`;
  }

  return "http://localhost:8000/api/v1";
}

export function buildApiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalized}`;
}
