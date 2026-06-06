"use client";

import React from "react";
import { Download, Square, Check, RefreshCw } from "lucide-react";
import Card from "../../../components/ui/Card";
import Button from "../../../components/ui/Button";
import styles from "../page.module.css";

const PIPELINE = [
  "INTAKE",
  "STATIC SCAN",
  "SANDBOX",
  "NETWORK",
  "ATTACK",
  "EXPLOIT",
  "SCORING",
  "REPORTER",
  "GOOGLE AGENT",
  "CLEANUP",
];

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
  activeStep: number;
  onOpenReport: (jobId: string) => void;
  onCancel: (jobId: string) => void;
  reportError: string;
}

function shortRepoName(repoUrl: string): string {
  return repoUrl.replace(/^https:\/\/github\.com\//, "").replace(/\/$/, "");
}

export default function PipelineViz({
  job,
  activeStep,
  onOpenReport,
  onCancel,
  reportError,
}: PipelineVizProps) {
  const isRunning = job ? ["queued", "running"].includes(job.status) : false;

  return (
    <Card variant="surface" className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>Maestro</div>
          <h2>{job ? shortRepoName(job.repo_url) : "No audit selected"}</h2>
        </div>
        <div className={styles.headerActions}>
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

      <div className={styles.pipeline}>
        {PIPELINE.map((phase, index) => {
          const isDone = activeStep > index;
          const isCurrent = activeStep === index;
          
          let stepClass = styles.pipelineStep;
          if (isDone) stepClass += ` ${styles.pipelineDone}`;
          if (isCurrent) stepClass += ` ${styles.pipelineCurrent}`;

          return (
            <div key={phase} className={stepClass}>
              <div className={styles.pipelineStepBadge}>
                {isDone ? (
                  <Check size={10} className={styles.checkIcon} />
                ) : isCurrent && isRunning ? (
                  <RefreshCw size={10} className={styles.spin} />
                ) : (
                  <span>{String(index).padStart(2, "0")}</span>
                )}
              </div>
              <strong className={styles.pipelineStepName}>{phase}</strong>
            </div>
          );
        })}
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
