"use client";

import React, { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAudits } from "../../../../features/audits/hooks";
import { useSSE } from "../../../../shared/hooks/useSSE";
import { useAuthSession } from "../../../../shared/hooks/useAuthSession";
import Card from "../../../../components/ui/Card";
import Button from "../../../../components/ui/Button";
import Badge from "../../../../components/ui/Badge";
import styles from "../../page.module.css";
import { formatDateTime, shortRepoName } from "../../../../shared/utils/format";
import { Download, ArrowLeft } from "lucide-react";
import LogStream from "../../../../features/audits/components/LogStream";
import AuditVerificationCard from "../../../../features/audits/components/AuditVerificationCard";
import { useToast } from "../../../../components/ui/Toast";

export default function AuditRunPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = Array.isArray(params.jobId) ? params.jobId[0] : params.jobId;
  const session = useAuthSession();

  const {
    selectedJobDetail,
    loadJobDetail,
    cancelAudit,
  } = useAudits(session.hasDashboardSession);

  const { logs, streamActive, startLogStream, stopLogStream } = useSSE({
    authenticated: session.hasDashboardSession,
    onJobStatusChange: () => {
      if (jobId) {
        void loadJobDetail(jobId);
      }
    }
  });

  useEffect(() => {
    if (jobId && session.hasDashboardSession) {
      void loadJobDetail(jobId);
      void startLogStream(jobId);
    }
    return () => {
      stopLogStream();
    };
  }, [jobId, session.hasDashboardSession, loadJobDetail, startLogStream, stopLogStream]);

  const { toast } = useToast();
  const prevStatusRef = React.useRef<string | null>(null);
  const job = selectedJobDetail?.job;

  useEffect(() => {
    if (job) {
      const prevStatus = prevStatusRef.current;
      if (prevStatus && prevStatus !== job.status) {
        if (["completed", "partial"].includes(job.status)) {
          const mailPart = job.email_delivered
            ? "Premium report sent to your mailbox."
            : "Email report skipped or failed.";
          const issuePart = job.github_issues_raised
            ? "Vulnerability tracking issues raised on GitHub."
            : "GitHub tracking issues skipped or not raised.";

          if (job.status === "completed") {
            toast(`Audit Job Completed! ${mailPart} ${issuePart}`, "success");
          } else {
            toast(`Audit Job completed partially! ${mailPart} ${issuePart}`, "info");
          }
        } else if (job.status === "failed") {
          toast(`Audit Job Failed! Please review execution console logs.`, "error");
        }
      }
      prevStatusRef.current = job.status;
    }
  }, [job, toast]);

  const isRunning = job ? ["queued", "running"].includes(job.status) : false;

  // Simple progress calculation based on logs
  let progress = 0;
  if (logs.length > 0) {
    // Estimate progress from log count as a rough heuristic
    progress = Math.min(90, Math.round((logs.length / 50) * 100));
  }
  if (job?.status === "completed" || job?.status === "failed" || job?.status === "cancelled") {
    progress = 100;
  }

  const renderTimeline = () => {
    const stages = [
      { id: "intake", label: "Intake", threshold: 0 },
      { id: "clone", label: "Clone", threshold: 15 },
      { id: "sast", label: "SAST/Secrets", threshold: 40 },
      { id: "deps", label: "Dependencies", threshold: 50 },
      { id: "dynamic", label: "Dynamic", threshold: 60 },
      { id: "ai", label: "AI/Fallback", threshold: 75 },
      { id: "report", label: "Report", threshold: 90 },
      { id: "complete", label: "Complete", threshold: 100 },
    ];

    return (
      <div className={styles.timelineWrapper} style={{ marginTop: "1rem", marginBottom: "2rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
          {stages.map((stage) => {
            const isActive = progress >= stage.threshold && progress < (stages[stages.indexOf(stage) + 1]?.threshold || 101);
            const isDone = progress > stage.threshold;
            return (
              <div key={stage.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", opacity: isDone || isActive ? 1 : 0.5 }}>
                <div style={{ width: "12px", height: "12px", borderRadius: "50%", background: isActive ? "#ff7208" : isDone ? "#00e676" : "#333", marginBottom: "4px" }} />
                <span style={{ fontSize: "11px", color: isActive ? "#fff" : "#9ca3af" }}>{stage.label}</span>
              </div>
            );
          })}
        </div>
        <div style={{ width: "100%", height: "4px", background: "#333", borderRadius: "2px", overflow: "hidden" }}>
          <div style={{ width: `${progress}%`, height: "100%", background: "linear-gradient(90deg, #ff4d08, #ffbf47)", transition: "width 0.5s ease" }} />
        </div>
      </div>
    );
  };

  if (!jobId) return <div>Invalid Job ID</div>;

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <div style={{ marginBottom: "1rem" }}>
            <Button variant="ghost" onClick={() => router.push("/dashboard")} size="sm">
              <ArrowLeft size={16} style={{ marginRight: 8 }} /> Back to Dashboard
            </Button>
        </div>

        <div className={styles.detailGrid}>
          <Card variant="surface" className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <div className={styles.sectionKicker}>Execution Console</div>
                <h2>{job ? shortRepoName(job.repo_url) : "Loading..."}</h2>
              </div>
              <div className={styles.headerActions}>
                {job && <Badge variant="status" type={job.cancel_requested && isRunning ? "cancelling" : job.status}>{job.cancel_requested && isRunning ? "cancelling" : job.status}</Badge>}
                {job?.report_pdf_url && (
                  <Button variant="secondary" size="sm" onClick={() => job.report_pdf_url && window.open(job.report_pdf_url, "_blank")}>
                    <Download size={14} /> Report
                  </Button>
                )}
                {job && isRunning && !job.cancel_requested && (
                  <Button variant="danger" size="sm" onClick={() => cancelAudit(job.id)}>
                     Cancel
                  </Button>
                )}
              </div>
            </div>

            <div className={styles.auditSummaryGrid}>
              <div className={styles.auditSummaryItem}>
                <span>Branch</span>
                <strong>{job?.repo_branch || "—"}</strong>
              </div>
              <div className={styles.auditSummaryItem}>
                <span>Started</span>
                <strong>{job ? formatDateTime(job.created_at) : "—"}</strong>
              </div>
              <div className={styles.auditSummaryItem}>
                <span>Progress</span>
                <strong>{progress}%</strong>
              </div>
            </div>

            {renderTimeline()}

            {job && ["failed", "cancelled"].includes(job.status) && job.error_message && (
              <div className={styles.noticeError} style={{ marginTop: "16px" }}>
                {job.error_message}
              </div>
            )}

            {job && (
              <AuditVerificationCard job={job} />
            )}

          </Card>
        </div>

        <div style={{ marginTop: "2rem" }}>
          <LogStream logs={logs} streamActive={streamActive && isRunning} hasSelection={true} />
        </div>
      </div>
    </main>
  );
}
