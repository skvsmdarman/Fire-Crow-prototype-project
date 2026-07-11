import { request } from "./request";

function toBase64ArrayBuffer(base64: string): ArrayBuffer {
  const normalized = base64.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0)).buffer as ArrayBuffer;
}

export async function enablePushNotifications(): Promise<string> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    return "Push is not available in this browser.";
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return "Notification permission was not granted.";
  }

  const registration = await navigator.serviceWorker.register("/sw.js");
  const { public_key } = await request<{ public_key: string }>("/push/vapid-public-key");
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: toBase64ArrayBuffer(public_key),
  });

  const keys = subscription.toJSON().keys ?? {};
  await request<{ status: string }>("/push/subscribe", {
    method: "POST",
    body: {
      endpoint: subscription.endpoint,
      p256dh: keys.p256dh ?? "",
      auth: keys.auth ?? "",
    },
  });

  return "Push alerts enabled for this workspace.";
}
