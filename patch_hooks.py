import re

with open("frontend/src/features/audits/hooks.ts", "r") as f:
    content = f.read()

hooks_replacement = """  const runAudit = useCallback(
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
        toast("Audit job successfully queued!", "success");
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
  );"""

new_hooks = """  const runAudit = useCallback(
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
  );"""

content = content.replace(hooks_replacement, new_hooks)

with open("frontend/src/features/audits/hooks.ts", "w") as f:
    f.write(content)
