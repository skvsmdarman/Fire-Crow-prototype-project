"use client";

import React, { useState } from "react";
import { Play } from "lucide-react";
import Card from "../../../components/ui/Card";
import Input from "../../../components/ui/Input";
import Button from "../../../components/ui/Button";
import styles from "../page.module.css";

interface AuditFormProps {
  onSubmit: (repoUrl: string, repoBranch: string) => Promise<void>;
  submitting: boolean;
  submitError: string;
}

export default function AuditForm({ onSubmit, submitting, submitError }: AuditFormProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [repoBranch, setRepoBranch] = useState("main");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void onSubmit(repoUrl, repoBranch);
  };

  return (
    <Card variant="surface" className={styles.panel} style={{ position: "relative", overflow: "hidden" }}>
      <div className={styles.authCardAccent} />
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>New Audit</div>
          <h2>Repository intake</h2>
        </div>
      </div>

      <form onSubmit={handleSubmit} className={styles.auditForm}>
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

        {submitError && (
          <div className={styles.noticeError} role="alert">
            {submitError}
          </div>
        )}

        <Button
          type="submit"
          variant="primary"
          loading={submitting}
          className={styles.submitButton}
        >
          {!submitting && <Play size={14} />}
          {submitting ? "Launching" : "Launch audit"}
        </Button>
      </form>
    </Card>
  );
}
