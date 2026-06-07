"use client";

import React from "react";
import { Download, FileWarning, GitBranch, Square } from "lucide-react";
import Card from "../../../components/ui/Card";
import Badge from "../../../components/ui/Badge";
import Button from "../../../components/ui/Button";
import styles from "../page.module.css";

interface Job {
  id: string;
  repo_url: string;
  repo_branch: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled" | "partial";
  created_at: string;
  cancel_requested: boolean;
  report_pdf_url: string | null;
  error_message: string | null;
}

interface PipelineVizProps {
  job: Job | null;
  onOpenReport: (jobId: string) => void;
  onCancel: (jobId: string) => void;
  reportError: string;
}

function shortRepoName(repoUrl: string): string {
  return repoUrl.replace(/^https:\/\/github\.com\//, "").replace(/\/$/, "");
}

function formatDateTime(value: string | null): string {
  if (!value) return "Pending";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusCopy(job: Job | null): string {
  if (!job) return "Select an audit to review its current state and available actions.";
  if (job.status === "queued") return "The audit is queued and waiting for the worker to begin.";
  if (job.status === "running") return "The audit is active. Live agent logs will continue streaming below.";
  if (job.status === "completed") return "The audit completed successfully and the report is ready when available.";
  if (job.status === "partial") return "The audit finished with partial results. Review findings and logs before exporting.";
  if (job.status === "cancelled") return "The audit was cancelled before full completion.";
  return "The audit stopped with an error. Review the saved logs for operational context.";
}

export default function PipelineViz({
  job,
  onOpenReport,
  onCancel,
  reportError,
}: PipelineVizProps) {
  const isRunning = job ? ["queued", "running"].includes(job.status) : false;

  return (
    <Card variant="surface" className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>Selected audit</div>
          <h2>{job ? shortRepoName(job.repo_url) : "No audit selected"}</h2>
        </div>
        <div className={styles.headerActions}>
          {job && <Badge variant="status" type={job.cancel_requested && isRunning ? "cancelling" : job.status}>{job.cancel_requested && isRunning ? "cancelling" : job.status}</Badge>}
          {job?.report_pdf_url && (
            <Button variant="secondary" size="sm" onClick={() => onOpenReport(job.id)}>
              <Download size={14} />
              Report
            </Button>
          )}
          {job && isRunning && !job.cancel_requested && (
            <Button variant="danger" size="sm" onClick={() => onCancel(job.id)}>
              <Square size={12} />
              Cancel
            </Button>
          )}
        </div>
      </div>

      <p className={styles.auditLead}>{statusCopy(job)}</p>

      <div className={styles.auditSummaryGrid}>
        <div className={styles.auditSummaryItem}>
          <span>Repository</span>
          <strong>{job ? shortRepoName(job.repo_url) : "—"}</strong>
        </div>
        <div className={styles.auditSummaryItem}>
          <span>Branch</span>
          <strong>{job?.repo_branch || "—"}</strong>
        </div>
        <div className={styles.auditSummaryItem}>
          <span>Created</span>
          <strong>{job ? formatDateTime(job.created_at) : "—"}</strong>
        </div>
        <div className={styles.auditSummaryItem}>
          <span>Report</span>
          <strong>{job?.report_pdf_url ? "Available" : "Not ready"}</strong>
        </div>
      </div>

      <div className={styles.auditStatusStrip}>
        <span><GitBranch size={13} /> Backend status only</span>
        <span><FileWarning size={13} /> No fake progress percentage</span>
      </div>

      {job && ["failed", "cancelled"].includes(job.status) && job.error_message && (
        <div className={styles.noticeError} style={{ marginTop: "16px" }}>
          {job.error_message}
        </div>
      )}
      {reportError && (
        <div className={styles.noticeError} style={{ marginTop: "16px" }}>
          {reportError}
        </div>
      )}
    </Card>
  );
}
