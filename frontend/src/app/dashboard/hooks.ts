import { useState, useCallback, useEffect } from "react";
import { useSystemStatus } from "../../features/system/hooks";
import { Job, Finding } from "../../features/audits/types";
import { useAuthSession } from "../../shared/hooks/useAuthSession";
import { useToast } from "../../components/ui/Toast";
import { fetchReportBlob } from "../../features/audits/api";
import { APIError } from "../../shared/api/errors";

export function useDashboardStatus(jobs: Job[], findings: Finding[]) {
  const { status: systemStatus, loading: loadingStatus, error: statusError, refetch: fetchSystemStatus } = useSystemStatus({
    autoPoll: true,
    pollInterval: 20000,
  });

  const runningCount = jobs.filter(j => j.status === "running").length;
  const criticalCount = findings.filter(f => f.severity === "critical").length;
  const latestCompleted = jobs.find(j => j.status === "completed" || j.status === "partial") || null;

  return {
    systemStatus,
    loadingStatus,
    statusError,
    fetchSystemStatus,
    runningCount,
    criticalCount,
    latestCompleted,
  };
}

export function useSessionValidation(router: { replace: (href: string) => void }) {
  const { validateSession, hasDashboardSession } = useAuthSession();
  const [isValidating, setIsValidating] = useState(true);
  const [isReconnecting, setIsReconnecting] = useState(false);

  const checkSession = useCallback(async () => {
    if (!hasDashboardSession) {
      router.replace("/signin");
      return;
    }

    try {
      const result = await validateSession();
      if (result === "invalid") {
        router.replace("/signin");
      } else if (result === "network_error") {
        setIsReconnecting(true);
        setIsValidating(false);
      } else {
        setIsReconnecting(false);
        setIsValidating(false);
      }
    } catch {
      setIsReconnecting(true);
      setIsValidating(false);
    }
  }, [hasDashboardSession, validateSession, router]);

  useEffect(() => {
    let active = true;
    const timer = setTimeout(() => {
      if (active) {
        void checkSession();
      }
    }, 0);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [checkSession]);

  return {
    isValidating,
    isReconnecting,
    refetchSession: checkSession,
  };
}

export function useAuditSubmission(runAudit: (p: { repo_url: string; repo_branch: string; attestation_accepted: boolean; authorization_scope: string }) => Promise<Job | null>) {
  const [newUrl, setNewUrl] = useState("");
  const [newBranch, setNewBranch] = useState("main");
  const [attestationAccepted, setAttestationAccepted] = useState(false);
  const [authorizationScope, setAuthorizationScope] = useState("authorized_representative");
  const [submitting, setSubmitting] = useState(false);
  const { toast } = useToast();

  const handleStartAudit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl.trim()) {
      toast("Repository URL is required.", "error");
      return;
    }
    if (!attestationAccepted) {
      toast("You must accept the security authorization attestation.", "error");
      return;
    }

    setSubmitting(true);
    try {
      const job = await runAudit({
        repo_url: newUrl.trim(),
        repo_branch: newBranch.trim() || "main",
        attestation_accepted: attestationAccepted,
        authorization_scope: authorizationScope,
      });
      if (job) {
        setNewUrl("");
        setNewBranch("main");
        setAttestationAccepted(false);
      }
    } catch (err) {
      console.error(err);
      toast("Failed to start audit.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return {
    newUrl,
    setNewUrl,
    newBranch,
    setNewBranch,
    attestationAccepted,
    setAttestationAccepted,
    authorizationScope,
    setAuthorizationScope,
    submitting,
    handleStartAudit,
  };
}

export function useReportDownload() {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const { toast } = useToast();

  const downloadReport = async (jobId: string, repoUrl: string) => {
    setDownloadingId(jobId);
    toast("Preparing report file download...", "info");
    try {
      const { blob } = await fetchReportBlob(jobId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      
      let repoName = "report";
      try {
        const parts = repoUrl.replace(/\.git$/, "").split("/");
        repoName = parts[parts.length - 1] || "report";
      } catch {
        // ignore
      }
      
      link.download = `firecrow_${repoName}_${jobId}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
      toast("Report download completed successfully.", "success");
    } catch (err) {
      console.error(err);
      let errorMsg = "Failed to download report.";
      if (err instanceof APIError) {
        errorMsg = err.message;
        if (err.requestId) {
          errorMsg += ` (Request ID: ${err.requestId})`;
        }
      } else if (err instanceof Error) {
        errorMsg = err.message;
      }
      toast(errorMsg, "error");
    } finally {
      setDownloadingId(null);
    }
  };

  return {
    downloadingId,
    downloadReport,
  };
}
