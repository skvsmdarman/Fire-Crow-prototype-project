"use client";

import React, { useMemo, useState } from "react";
import { GitBranch, Play, ShieldCheck } from "lucide-react";
import Card from "../../../components/ui/Card";
import Input from "../../../components/ui/Input";
import Button from "../../../components/ui/Button";
import styles from "../../../app/dashboard/page.module.css";
import mobile from "../../../app/dashboard/mobile.module.css";

interface AuditFormProps {
  onSubmit: (repoUrl: string, repoBranch: string) => Promise<void>;
  submitting: boolean;
  submitError: string | null;
}

export default function AuditForm({ onSubmit, submitting, submitError }: AuditFormProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [repoBranch, setRepoBranch] = useState("main");
  const [localError, setLocalError] = useState("");

  const normalizedRepoUrl = useMemo(() => repoUrl.trim(), [repoUrl]);
  const normalizedRepoBranch = useMemo(() => repoBranch.trim() || "main", [repoBranch]);
  const canSubmit = normalizedRepoUrl.length > 0 && !submitting;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!normalizedRepoUrl) {
      setLocalError("Repository URL is required.");
      return;
    }
    setLocalError("");
    void onSubmit(normalizedRepoUrl, normalizedRepoBranch);
  };

  return (
    <Card variant="surface" className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>New audit</div>
          <h2>Start an audit</h2>
        </div>
        <span className={mobile.intakeBadge}>GitHub HTTPS only</span>
      </div>

      <form onSubmit={handleSubmit} className={styles.auditForm}>
        <section className={mobile.intakePanel} aria-labelledby="audit-intake-title">
          <div className={mobile.intakeHero}>
            <div className={mobile.intakeIcon} aria-hidden="true">
              <ShieldCheck size={18} />
            </div>
            <div>
              <h3 id="audit-intake-title">Authorized repository intake</h3>
              <p>Submit the GitHub repository URL and branch you want the backend to audit.</p>
            </div>
          </div>

          <div className={mobile.intakeMeta}>
            <div className={mobile.intakeMetaCard}>
              <GitBranch size={14} />
              <div>
                <strong>Accepted source</strong>
                <span>GitHub HTTPS repository URL</span>
              </div>
            </div>
            <div className={mobile.intakeMetaCard}>
              <ShieldCheck size={14} />
              <div>
                <strong>Boundary</strong>
                <span>Only audit repositories you own or are authorized to test</span>
              </div>
            </div>
          </div>

          <div className={mobile.intakeFields}>
            <Input
              label="Repository URL"
              placeholder="https://github.com/org/repository"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              disabled={submitting}
            />
            <Input
              label="Branch or ref"
              placeholder="main"
              value={repoBranch}
              onChange={(e) => setRepoBranch(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div className={mobile.intakeSummary}>
            <div className={mobile.intakeSummaryRow}>
              <span>Repository</span>
              <strong>{normalizedRepoUrl || "Not set"}</strong>
            </div>
            <div className={mobile.intakeSummaryRow}>
              <span>Branch</span>
              <strong>{normalizedRepoBranch}</strong>
            </div>
          </div>

          <div className={mobile.safetyNote}>
            The client sends only the repository URL and branch. Extra decorative scope or sandbox selections have been removed because they were not part of the real backend contract.
          </div>
        </section>

        {(localError || submitError) && <div className={styles.noticeError} role="alert">{localError || submitError}</div>}

        <div className={mobile.intakeActions}>
          <Button type="submit" variant="primary" loading={submitting} className={styles.submitButton} disabled={!canSubmit}>
            {!submitting && <Play size={14} />}
            {submitting ? "Launching" : "Start audit"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
