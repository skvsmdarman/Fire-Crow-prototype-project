import { useState, useCallback, useEffect } from "react";
import { Job, JobDetail, SubmitAuditBody } from "./types";
import { fetchJobs, fetchJobDetail, submitAudit, cancelJob } from "./api";
import { useToast } from "../../components/ui/Toast";

export function useAudits(token: string | null) {
  const { toast } = useToast();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [jobsError, setJobsError] = useState<string | null>(null);

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJobDetail, setSelectedJobDetail] = useState<JobDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    if (!token) return;
    setLoadingJobs(true);
    setJobsError(null);
    try {
      const data = await fetchJobs();
      setJobs(data);
    } catch (err) {
      const error = err as { message?: string };
      setJobsError(error.message || "Failed to load audit history.");
    } finally {
      setLoadingJobs(false);
    }
  }, [token]);

  const loadJobDetail = useCallback(async (jobId: string) => {
    if (!token) return;
    setLoadingDetail(true);
    setDetailError(null);
    try {
      const detail = await fetchJobDetail(jobId);
      setSelectedJobDetail(detail);
    } catch (err) {
      const error = err as { message?: string };
      setDetailError(error.message || "Failed to load audit details.");
    } finally {
      setLoadingDetail(false);
    }
  }, [token]);

  const runAudit = useCallback(
    async (body: SubmitAuditBody) => {
      if (!token) {
        setSubmitError("Connect a workspace before launching an audit.");
        return null;
      }
      setSubmitting(true);
      setSubmitError(null);
      toast("Submitting repository intake request...", "info");
      try {
        const job = await submitAudit(body);
        setSelectedJobId(job.id);
        await loadJobs();
        toast("Audit job successfully queued! Redirecting to execution console...", "success");
        // We will return the job so the component can redirect
        return job;
      } catch (err) {
        const error = err as { message?: string };
        const msg = error.message || "Unable to launch audit.";
        setSubmitError(msg);
        toast(msg, "error");
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [token, loadJobs, toast]
  );

  const cancelAudit = useCallback(
    async (jobId: string) => {
      if (!token) return;
      toast("Requesting job cancellation...", "info");
      try {
        await cancelJob(jobId);
        await loadJobs();
        if (selectedJobId === jobId) {
          await loadJobDetail(jobId);
        }
        toast("Cancellation request transmitted.", "success");
      } catch (err) {
        const error = err as { message?: string };
        toast(error.message || "Unable to cancel job.", "error");
      }
    },
    [token, selectedJobId, loadJobs, loadJobDetail, toast]
  );

  useEffect(() => {
    if (token) {
      const timer = setTimeout(() => {
        void loadJobs();
      }, 0);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setJobs([]);
        setSelectedJobId(null);
        setSelectedJobDetail(null);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [token, loadJobs]);

  useEffect(() => {
    if (selectedJobId) {
      const timer = setTimeout(() => {
        void loadJobDetail(selectedJobId);
      }, 0);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setSelectedJobDetail(null);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [selectedJobId, loadJobDetail]);

  return {
    jobs,
    loadingJobs,
    jobsError,
    selectedJobId,
    setSelectedJobId,
    selectedJobDetail,
    loadingDetail,
    detailError,
    submitting,
    submitError,
    setSubmitError,
    loadJobs,
    loadJobDetail,
    runAudit,
    cancelAudit,
  };
}
export default useAudits;
