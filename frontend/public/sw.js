const CACHE_NAME = 'firecrow-v1';
const OFFLINE_URL = '/offline';

// Static assets to cache for offline use (app shell only - no sensitive data)
const PRECACHE_URLS = [
  '/',
  '/offline',
  '/signin',
  '/favicon.ico',
];

// Install: Cache app shell
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(PRECACHE_URLS);
      })
      .then(function() {
        return self.skipWaiting();
      })
  );
});

// Activate: Clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys()
      .then(function(cacheNames) {
        return Promise.all(
          cacheNames
            .filter(function(cacheName) {
              return cacheName !== CACHE_NAME;
            })
            .map(function(cacheName) {
              return caches.delete(cacheName);
            })
        );
      })
      .then(function() {
        return self.clients.claim();
      })
  );
});

// Fetch: Network-first for API calls, cache-first for static assets
self.addEventListener('fetch', function(event) {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip API calls - always go to network (no sensitive data cached)
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) {
    event.respondWith(
      fetch(event.request)
        .catch(function() {
          // API calls fail with offline error - don't cache
          return new Response(JSON.stringify({ error: 'offline', message: 'You are offline. Please check your connection.' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  // Static assets: Cache first, network fallback
  event.respondWith(
    caches.match(event.request)
      .then(function(cachedResponse) {
        if (cachedResponse) {
          // Return cached version, fetch updated version in background
          event.waitUntil(
            fetch(event.request)
              .then(function(networkResponse) {
                if (networkResponse && networkResponse.status === 200) {
                  caches.open(CACHE_NAME).then(function(cache) {
                    cache.put(event.request, networkResponse);
                  });
                }
              })
              .catch(function() {
                // Network failed, cached version is fine
              })
          );
          return cachedResponse;
        }

        // Not in cache, fetch from network
        return fetch(event.request)
          .then(function(networkResponse) {
            if (networkResponse && networkResponse.status === 200) {
              const responseClone = networkResponse.clone();
              caches.open(CACHE_NAME).then(function(cache) {
                cache.put(event.request, responseClone);
              });
            }
            return networkResponse;
          })
          .catch(function() {
            // Network failed and not in cache
            // For navigation requests, show offline page
            if (event.request.mode === 'navigate') {
              return caches.match(OFFLINE_URL);
            }
            // For other requests, return a basic error
            return new Response('Offline', { status: 503 });
          });
      })
  );
});

// Push notifications
self.addEventListener('push', function(event) {
  if (event.data) {
    try {
      const payload = event.data.json();
      const options = {
        body: payload.body || 'Fire Crow update',
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        data: payload
      };
      event.waitUntil(
        self.registration.showNotification(payload.title || 'Fire Crow Alert', options)
      );
    } catch (e) {
      event.waitUntil(
        self.registration.showNotification('Fire Crow Alert', {
          body: event.data.text()
        })
      );
    }
  }
});

// Notification click
self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('/dashboard')
  );
});
