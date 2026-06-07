"use client";

import React from "react";
import { motion } from "framer-motion";
import { Terminal, RefreshCw } from "lucide-react";
import Card from "../../../components/ui/Card";
import Badge from "../../../components/ui/Badge";
import Button from "../../../components/ui/Button";
import { staggerFast, springUp } from "../../../lib/animations";
import styles from "../page.module.css";

interface Job {
  id: string;
  user_id: string;
  repo_url: string;
  repo_branch: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled" | "partial";
  created_at: string;
  finished_at: string | null;
  cancel_requested: boolean;
  cancel_requested_at: string | null;
  report_pdf_url: string | null;
  error_message: string | null;
}

interface JobListProps {
  jobs: Job[];
  selectedJobId: string | null;
  loadingJobs: boolean;
  onRefresh: () => void;
  onJobSelect: (jobId: string) => void;
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

function statusLabel(job: Job): "queued" | "running" | "completed" | "failed" | "cancelled" | "partial" | "cancelling" {
  if (job.cancel_requested && !["completed", "failed", "cancelled", "partial"].includes(job.status)) {
    return "cancelling";
  }
  return job.status;
}

export default function JobList({
  jobs,
  selectedJobId,
  loadingJobs,
  onRefresh,
  onJobSelect,
}: JobListProps) {
  return (
    <Card variant="surface" className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>Audit list</div>
          <h2>Recent audits</h2>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          disabled={loadingJobs}
          className={styles.refreshButton}
        >
          <RefreshCw className={loadingJobs ? styles.spin : ""} size={12} />
          Refresh
        </Button>
      </div>

      <motion.div
        variants={staggerFast}
        initial="hidden"
        animate="visible"
        className={styles.jobList}
      >
        {jobs.length === 0 ? (
          <div className={styles.emptyState}>No audits in this workspace.</div>
        ) : (
          jobs.map((job) => {
            const isActive = job.id === selectedJobId;
            return (
              <motion.button
                variants={springUp}
                key={job.id}
                className={[
                  styles.jobRow,
                  isActive ? styles.jobRowActive : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                type="button"
                onClick={() => onJobSelect(job.id)}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeJobIndicator"
                    className={styles.activeJobIndicator}
                    transition={{ type: "spring", stiffness: 350, damping: 25 }}
                  />
                )}
                <span className={styles.jobInfo}>
                  <Terminal size={14} className={styles.jobIcon} />
                  <span className={styles.jobMetaBlock}>
                    <strong>{shortRepoName(job.repo_url)}</strong>
                    <small>
                      Branch {job.repo_branch} / {formatDateTime(job.created_at)}
                    </small>
                  </span>
                </span>
                <Badge variant="status" type={statusLabel(job)} pulse={statusLabel(job) === "running"}>
                  {statusLabel(job)}
                </Badge>
              </motion.button>
            );
          })
        )}
      </motion.div>
    </Card>
  );
}
