import { useState, useEffect, useCallback } from "react";
import { SystemStatus } from "./types";
import { getSystemStatus } from "./api";

interface UseSystemStatusOptions {
  autoPoll?: boolean;
  pollInterval?: number;
}

export function useSystemStatus({ autoPoll = false, pollInterval = 15000 }: UseSystemStatusOptions = {}) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setError(null);
      const data = await getSystemStatus();
      setStatus(data);
    } catch (err) {
      const error = err as { message?: string };
      setError(error.message || "Failed to fetch system status.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchStatus();
    }, 0);

    if (!autoPoll) {
      return () => clearTimeout(timer);
    }

    const interval = setInterval(() => {
      void fetchStatus();
    }, pollInterval);

    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [fetchStatus, autoPoll, pollInterval]);

  return {
    status,
    loading,
    error,
    refetch: fetchStatus,
  };
}
export default useSystemStatus;
