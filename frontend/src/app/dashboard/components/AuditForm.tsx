"use client";

import React, { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Play, ShieldCheck } from "lucide-react";
import Card from "../../../components/ui/Card";
import Input from "../../../components/ui/Input";
import Button from "../../../components/ui/Button";
import styles from "../page.module.css";
import mobile from "../mobile.module.css";

interface AuditFormProps {
  onSubmit: (repoUrl: string, repoBranch: string) => Promise<void>;
  submitting: boolean;
  submitError: string;
}

type WizardStep = 0 | 1 | 2 | 3 | 4;

const WIZARD_STEPS = ["Source", "Repository", "Scope", "Sandbox", "Review"] as const;

const DEFENSIVE_SCOPES = [
  "Dependency risk",
  "Secret/config exposure",
  "Auth/session review",
  "Static code analysis",
  "API security review",
  "Infrastructure/config review",
] as const;

export default function AuditForm({ onSubmit, submitting, submitError }: AuditFormProps) {
  const [step, setStep] = useState<WizardStep>(0);
  const [repoUrl, setRepoUrl] = useState("");
  const [repoBranch, setRepoBranch] = useState("main");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(() => [...DEFENSIVE_SCOPES]);
  const [localError, setLocalError] = useState("");

  const canMoveNext = useMemo(() => step !== 1 || repoUrl.trim().length > 0, [repoUrl, step]);

  const nextStep = () => {
    if (!canMoveNext) {
      setLocalError("Repository URL is required before review can continue.");
      return;
    }
    setLocalError("");
    setStep((current) => Math.min(current + 1, WIZARD_STEPS.length - 1) as WizardStep);
  };

  const previousStep = () => {
    setLocalError("");
    setStep((current) => Math.max(current - 1, 0) as WizardStep);
  };

  const toggleScope = (scope: string) => {
    setSelectedScopes((current) =>
      current.includes(scope) ? current.filter((item) => item !== scope) : [...current, scope],
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) {
      setLocalError("Repository URL is required.");
      setStep(1);
      return;
    }
    setLocalError("");
    void onSubmit(repoUrl, repoBranch);
  };

  return (
    <Card variant="surface" className={styles.panel} style={{ position: "relative", overflow: "hidden" }}>
      <div className={styles.authCardAccent} />
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>New Audit</div>
          <h2>Authorized audit wizard</h2>
        </div>
        <span className={mobile.wizardStepPill}>Step {step + 1} of {WIZARD_STEPS.length}</span>
      </div>

      <ol className={mobile.wizardProgress} aria-label="Audit setup progress">
        {WIZARD_STEPS.map((label, index) => (
          <li
            key={label}
            className={[mobile.wizardProgressStep, index === step ? mobile.wizardProgressActive : "", index < step ? mobile.wizardProgressDone : ""]
              .filter(Boolean)
              .join(" ")}
          >
            <span>{index < step ? <CheckCircle2 size={12} /> : index + 1}</span>
            <strong>{label}</strong>
          </li>
        ))}
      </ol>

      <form onSubmit={handleSubmit} className={styles.auditForm}>
        {step === 0 && (
          <section className={mobile.wizardPanel} aria-labelledby="audit-source-title">
            <div className={mobile.wizardIconCard} aria-hidden="true">
              <ShieldCheck size={22} />
            </div>
            <div>
              <h3 id="audit-source-title">Choose source</h3>
              <p>Fire Crow currently accepts authorized repository URLs through the existing backend intake contract.</p>
            </div>
            <div className={mobile.optionCardActive}>
              <strong>Git repository</strong>
              <span>Use a repository you own or have explicit permission to test.</span>
            </div>
            <div className={mobile.safetyNote}>Only audit systems you own or are authorized to test. Fire Crow keeps guidance remediation-focused.</div>
          </section>
        )}

        {step === 1 && (
          <section className={mobile.wizardPanel} aria-labelledby="repo-details-title">
            <div>
              <h3 id="repo-details-title">Repository details</h3>
              <p>Enter the repository URL and branch or ref that the backend should audit.</p>
            </div>
            <Input label="Repository URL" placeholder="https://github.com/org/repository" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} disabled={submitting} />
            <Input label="Branch or ref" placeholder="main" value={repoBranch} onChange={(e) => setRepoBranch(e.target.value)} disabled={submitting} />
          </section>
        )}

        {step === 2 && (
          <section className={mobile.wizardPanel} aria-labelledby="audit-scope-title">
            <div>
              <h3 id="audit-scope-title">Audit scope</h3>
              <p>Select defensive review areas for the pre-flight checklist. The current backend preserves its existing repository-and-ref API contract.</p>
            </div>
            <div className={mobile.scopeGrid}>
              {DEFENSIVE_SCOPES.map((scope) => {
                const checked = selectedScopes.includes(scope);
                return (
                  <button key={scope} type="button" className={checked ? mobile.scopeChipActive : mobile.scopeChip} aria-pressed={checked} onClick={() => toggleScope(scope)}>
                    <span>{checked ? "Included" : "Optional"}</span>
                    <strong>{scope}</strong>
                  </button>
                );
              })}
            </div>
          </section>
        )}

        {step === 3 && (
          <section className={mobile.wizardPanel} aria-labelledby="sandbox-options-title">
            <div>
              <h3 id="sandbox-options-title">Sandbox and safety</h3>
              <p>The backend decides the active sandbox mode from its configured runtime and system status.</p>
            </div>
            <div className={mobile.reviewGrid}>
              <div className={mobile.reviewCard}><span>Runtime mode</span><strong>Backend configured</strong></div>
              <div className={mobile.reviewCard}><span>Validation boundary</span><strong>Authorization-only</strong></div>
              <div className={mobile.reviewCard}><span>Output style</span><strong>Evidence + remediation</strong></div>
            </div>
            <div className={mobile.safetyNote}>The mobile client does not add offensive payload controls or bypass backend authorization checks.</div>
          </section>
        )}

        {step === 4 && (
          <section className={mobile.wizardPanel} aria-labelledby="review-start-title">
            <div>
              <h3 id="review-start-title">Review and start</h3>
              <p>Confirm the authorized target before submitting the audit to the existing backend.</p>
            </div>
            <div className={mobile.reviewGrid}>
              <div className={mobile.reviewCard}><span>Repository</span><strong>{repoUrl.trim() || "Not provided"}</strong></div>
              <div className={mobile.reviewCard}><span>Branch/ref</span><strong>{repoBranch.trim() || "main"}</strong></div>
              <div className={mobile.reviewCard}><span>Defensive scope</span><strong>{selectedScopes.length} areas selected</strong></div>
            </div>
          </section>
        )}

        {(localError || submitError) && <div className={styles.noticeError} role="alert">{localError || submitError}</div>}

        <div className={mobile.stickyBottomActions}>
          <Button type="button" variant="ghost" onClick={previousStep} disabled={step === 0 || submitting}><ArrowLeft size={14} />Back</Button>
          {step < WIZARD_STEPS.length - 1 ? (
            <Button type="button" variant="primary" onClick={nextStep} disabled={submitting}>Next<ArrowRight size={14} /></Button>
          ) : (
            <Button type="submit" variant="primary" loading={submitting} className={styles.submitButton}>{!submitting && <Play size={14} />}{submitting ? "Launching" : "Start audit"}</Button>
          )}
        </div>
      </form>
    </Card>
  );
}
