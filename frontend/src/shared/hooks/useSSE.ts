import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../api/client";

export interface LogLine {
  id: number;
  agent_name: string;
  log_level: string;
  message: string;
  timestamp: string;
}

interface UseSSEOptions {
  authenticated: boolean;
  token: string | null;
  onJobStatusChange?: () => void;
  maxLogs?: number;
}

export function useSSE({ authenticated, token, onJobStatusChange, maxLogs = 500 }: UseSSEOptions) {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [streamActive, setStreamActive] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const onJobStatusChangeRef = useRef(onJobStatusChange);
  useEffect(() => {
    onJobStatusChangeRef.current = onJobStatusChange;
  }, [onJobStatusChange]);

  const stopLogStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStreamActive(false);
  }, []);

  const startLogStream = useCallback(
    async (jobId: string) => {
      if (!authenticated) return;
      stopLogStream();
      setLogs([]);
      setStreamActive(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
        const response = await fetch(`${API_BASE_URL}/audit/${jobId}/stream`, {
          credentials: "include",
          headers,
          signal: controller.signal,
        });

        if (response.status === 401 || response.status === 403) {
          // Auth client middleware will redirect automatically, but we stop the stream here
          stopLogStream();
          return;
        }

        if (!response.body) {
          throw new Error("Log stream unavailable.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const rawLine of lines) {
            const trimmedLine = rawLine.trim();
            if (!trimmedLine) continue; // Keepalive/empty comments

            if (!trimmedLine.startsWith("data:")) continue;
            const payload = trimmedLine.replace("data:", "").trim();

            try {
              const parsed = JSON.parse(payload);
              if (parsed.message) {
                setLogs((prev) => {
                  const updated = [...prev, parsed as LogLine];
                  if (updated.length > maxLogs) {
                    return updated.slice(updated.length - maxLogs);
                  }
                  return updated;
                });
              }
              if (parsed.status && onJobStatusChangeRef.current) {
                onJobStatusChangeRef.current();
              }
            } catch {
              // Ignore non-JSON stream fragments
            }
          }
        }
      } catch (err) {
        const error = err as { name?: string; message?: string };
        if (error.name !== "AbortError") {
          setLogs((prev) => [
            ...prev,
            {
              id: Date.now(),
              agent_name: "SYSTEM",
              log_level: "ERROR",
              message: error.message || "Log stream disconnected.",
              timestamp: new Date().toISOString(),
            },
          ]);
        }
      } finally {
        setStreamActive(false);
      }
    },
    [authenticated, token, stopLogStream, maxLogs]
  );

  return {
    logs,
    streamActive,
    startLogStream,
    stopLogStream,
    setLogs,
  };
}
