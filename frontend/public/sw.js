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

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('/dashboard')
  );
});
