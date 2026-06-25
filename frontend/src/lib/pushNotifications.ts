// Utility to subscribe user to Web Push notifications
import { buildApiUrl } from "../shared/api/baseUrl";

function urlBase64ToUint8Array(base64String: string) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export async function subscribeUserToPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.warn('Push notifications are not supported in this browser.');
    return;
  }

  try {
    // Request permission first
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      console.warn('Notification permission denied.');
      return;
    }

    // Register service worker if not already registered
    await navigator.serviceWorker.register('/sw.js');
    const registration = await navigator.serviceWorker.ready;
    if (!registration.active) {
      throw new Error('No active Service Worker available for subscription.');
    }
    console.log('Service Worker active and ready:', registration);

    // Fetch VAPID public key from backend
    const res = await fetch(buildApiUrl('/push/vapid-public-key'), {
      credentials: "include",
    });
    if (!res.ok) throw new Error('Failed to fetch VAPID public key');
    const { public_key } = await res.json();

    const applicationServerKey = urlBase64ToUint8Array(public_key);

    // Subscribe to push manager
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey
    });

    // Extract keys
    const rawSubscription = JSON.parse(JSON.stringify(subscription));
    const p256dh = rawSubscription.keys.p256dh;
    const auth = rawSubscription.keys.auth;

    // Send subscription to backend
    const subscribeRes = await fetch(buildApiUrl('/push/subscribe'), {
      method: 'POST',
      credentials: "include",
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        endpoint: subscription.endpoint,
        p256dh,
        auth
      })
    });

    if (subscribeRes.ok) {
      console.log('Successfully subscribed to push notifications!');
    } else {
      console.error('Failed to register subscription on backend.');
    }
  } catch (err: unknown) {
    const errorObj = err as Record<string, unknown> | null | undefined;
    const name = errorObj && typeof errorObj === 'object' && typeof errorObj.name === 'string' ? errorObj.name : '';
    const message = errorObj && typeof errorObj === 'object' && typeof errorObj.message === 'string' ? errorObj.message : '';
    
    const isExpectedBrowserError = 
      name === 'AbortError' || 
      name === 'NotAllowedError' || 
      name === 'InvalidStateError' || 
      name === 'SecurityError' ||
      message.includes('Registration failed') ||
      message.includes('push service error');
    
    if (isExpectedBrowserError) {
      console.warn(`Push subscription registration skipped/unavailable: ${name || 'AbortError'} - ${message || 'Registration failed - push service error'}`);
    } else {
      console.error('Error subscribing to push notifications:', err);
    }
  }
}
