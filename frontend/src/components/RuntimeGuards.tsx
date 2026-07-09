"use client";

import { useEffect } from "react";

export function RuntimeGuards() {
  useEffect(() => {
    function onUnhandledRejection(event: PromiseRejectionEvent) {
      const reason = event.reason;
      if (
        reason &&
        typeof reason === "object" &&
        !(reason instanceof Error) &&
        ("isTrusted" in reason || "type" in reason)
      ) {
        event.preventDefault();
      }
    }

    window.addEventListener("unhandledrejection", onUnhandledRejection, true);
    return () => {
      window.removeEventListener("unhandledrejection", onUnhandledRejection, true);
    };
  }, []);

  return null;
}
