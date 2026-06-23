"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import styles from "./PipelineDemoSection.module.css";

interface PipelineStep {
  name: string;
  desc: string;
  findings: Array<{
    idx: string;
    title: string;
    desc: string;
    severity: "Critical" | "High" | "Medium" | "Low";
  }>;
  graph: string;
}

const pipelineSteps: PipelineStep[] = [
  {
    name: "Reconnaissance",
    desc: "Subdomain discovery, endpoint enumeration, and technology fingerprinting.",
    findings: [],
    graph: "Discovered 4 public endpoints, 1 internal gateway interface."
  },
  {
    name: "Threat Modeling",
    desc: "Attack tree generation and automated trust-boundary mapping.",
    findings: [
      { idx: "04", title: "Unauthenticated Gateway Route", desc: "Public ingress routes directly to db-connector", severity: "Medium" }
    ],
    graph: "Entry path identified: Public Gateway → API Handler → DB Endpoint."
  },
  {
    name: "SAST Analysis",
    desc: "Semgrep and custom security rule-matching across all repository branches.",
    findings: [
      { idx: "01", title: "Hardcoded Secret Key", desc: "Fallback JWT secret in backend/app/config.py:192", severity: "Critical" },
      { idx: "04", title: "Unauthenticated Gateway Route", desc: "Public ingress routes directly to db-connector", severity: "Medium" }
    ],
    graph: "Vulnerability trace: config.py (credentials) → potential token forging."
  },
  {
    name: "Dependency Scan",
    desc: "OSV database cross-correlation for packages and container layers.",
    findings: [
      { idx: "01", title: "Hardcoded Secret Key", desc: "Fallback JWT secret in backend/app/config.py:192", severity: "Critical" },
      { idx: "03", title: "CVE-2023-45857 (Axios)", desc: "Axios < 1.6.0 vulnerable to SSRF redirection", severity: "High" },
      { idx: "04", title: "Unauthenticated Gateway Route", desc: "Public ingress routes directly to db-connector", severity: "Medium" }
    ],
    graph: "Supply chain mapping completed: 3 outdated library CVEs identified."
  },
  {
    name: "Dynamic Attack",
    desc: "Verification of exploit paths inside secure, isolated sandboxes.",
    findings: [
      { idx: "01", title: "Hardcoded Secret Key", desc: "Fallback JWT secret in backend/app/config.py:192", severity: "Critical" },
      { idx: "02", title: "SQL Injection", desc: "Raw concatenation discovered in user router", severity: "High" },
      { idx: "03", title: "CVE-2023-45857 (Axios)", desc: "Axios < 1.6.0 vulnerable to SSRF redirection", severity: "High" },
      { idx: "04", title: "Unauthenticated Gateway Route", desc: "Public ingress routes directly to db-connector", severity: "Medium" }
    ],
    graph: "Exploit validated in sandbox: JWT spoofing bypasses authentication."
  }
];

export default function PipelineDemoSection() {
  const [activeStep, setActiveStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % pipelineSteps.length);
    }, 4000);

    return () => clearInterval(interval);
  }, [isPlaying]);

  const selectStep = (index: number) => {
    setActiveStep(index);
    setIsPlaying(false);
  };

  const currentStepData = pipelineSteps[activeStep];

  return (
    <section className={styles.section} id="pipeline">
      <div className={styles.sectionHeader}>
        <div>
          <span className={styles.eyebrow}>Agentic Pipeline</span>
          <h2 className={styles.sectionTitle}>Pipeline in action</h2>
        </div>
        <p className={styles.sectionIntro}>
          Specialized agents orchestrate sequentially. Watch the dynamic results dashboard update in real-time as vulnerabilities are discovered and sandbox verified.
        </p>
      </div>

      <div className={styles.container}>
        <div className={styles.stepsColumn}>
          <div className={styles.stepsHeader}>
            <span>Pipeline Steps</span>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className={styles.playButton}
              title={isPlaying ? "Pause autoplay" : "Resume autoplay"}
            >
              {isPlaying ? (
                <svg viewBox="0 0 24 24" fill="currentColor" className={styles.playIcon}>
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="currentColor" className={styles.playIcon}>
                  <polygon points="5,3 19,12 5,21" />
                </svg>
              )}
              {isPlaying ? "Pause Autoplay" : "Autoplay"}
            </button>
          </div>

          <div className={styles.stepsList}>
            {pipelineSteps.map((step, idx) => {
              const isActive = activeStep === idx;
              const isCompleted = idx < activeStep;
              return (
                <button
                  key={step.name}
                  onClick={() => selectStep(idx)}
                  className={`${styles.stepCard} ${isActive ? styles.stepCardActive : ""} ${isCompleted ? styles.stepCardCompleted : ""}`}
                >
                  <div className={styles.stepIndicator}>
                    {isCompleted ? (
                      <span className={styles.checkMark}>✓</span>
                    ) : (
                      <span className={styles.stepNum}>{idx + 1}</span>
                    )}
                  </div>
                  <div className={styles.stepInfo}>
                    <h4 className={styles.stepName}>{step.name}</h4>
                    <p className={styles.stepDesc}>{step.desc}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className={styles.boardColumn}>
          <div className={styles.board}>
            <div className={styles.boardHeader}>
              <div>
                <span className={styles.boardSub}>CURRENT DEMO SCAN</span>
                <h3 className={styles.boardTitle}>acme/backend-api</h3>
              </div>
              <div className={styles.badgeGroup}>
                <span className={styles.boardBadge}>ACTIVE STAGE: {currentStepData.name.toUpperCase()}</span>
              </div>
            </div>

            <div className={styles.boardBody}>
              <div className={styles.findingsHeader}>
                <span>Discovered Vulnerabilities ({currentStepData.findings.length})</span>
              </div>

              <div className={styles.findingsList}>
                <AnimatePresence mode="popLayout">
                  {currentStepData.findings.length === 0 ? (
                    <motion.div
                      key="empty"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className={styles.emptyState}
                    >
                      <p>Initializing scan... No vulnerabilities registered yet in the current pipeline stage.</p>
                    </motion.div>
                  ) : (
                    currentStepData.findings.map((f) => (
                      <motion.div
                        key={f.idx}
                        layout
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className={styles.findingCard}
                      >
                        <span className={styles.findingIndex}>{f.idx}</span>
                        <div className={styles.findingContent}>
                          <h5 className={styles.findingTitle}>{f.title}</h5>
                          <p className={styles.findingDesc}>{f.desc}</p>
                        </div>
                        <span className={`${styles.severityBadge} ${styles[f.severity.toLowerCase()]}`}>
                          {f.severity}
                        </span>
                      </motion.div>
                    ))
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div className={styles.boardFooter}>
              <div>
                <span className={styles.footerLabel}>Pipeline Graph Node State</span>
                <p className={styles.footerText}>{currentStepData.graph}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
