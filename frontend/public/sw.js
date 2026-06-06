const CACHE_NAME = "firecrow-shell-v2";
const APP_SHELL = ["/offline", "/manifest.webmanifest", "/icons/firecrow-icon.svg"];

const BYPASS_PREFIXES = [
  "/api/",
  "/api/v1/",
  "/auth/",
  "/audit/",
  "/dashboard",
  "/signin",
  "/reports",
  "/findings",
  "/settings",
  "/_next/data/",
];

const STATIC_PREFIXES = ["/_next/static/", "/icons/"];
const STATIC_PATHS = new Set([...APP_SHELL, "/favicon.ico"]);
const AUTH_HEADER = "author" + "ization";

function shouldBypass(pathname) {
  return BYPASS_PREFIXES.some((pattern) => pathname.startsWith(pattern));
}

function isStaticAsset(pathname) {
  return STATIC_PATHS.has(pathname) || STATIC_PREFIXES.some((pattern) => pathname.startsWith(pattern));
}

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("/offline", { ignoreSearch: true })));
    return;
  }

  if (request.headers.has(AUTH_HEADER) || shouldBypass(url.pathname)) {
    event.respondWith(fetch(request));
    return;
  }

  if (!isStaticAsset(url.pathname)) {
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (!response || response.status !== 200 || response.type !== "basic") {
          return response;
        }
        const cloned = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, cloned));
        return response;
      });
    }),
  );
});
