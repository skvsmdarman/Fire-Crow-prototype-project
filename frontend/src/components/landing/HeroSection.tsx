"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import styles from "./HeroSection.module.css";

interface HeroSectionProps {
  isLoggedIn: boolean;
  onEnter: () => void;
}

const DEFAULT_REPO = "github.com/acme/backend-api";

export default function HeroSection({ isLoggedIn, onEnter }: HeroSectionProps) {
  const [repoInput, setRepoInput] = useState(DEFAULT_REPO);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [logs, setLogs] = useState<Array<{ text: string; type: "info" | "success" | "warning" | "error" }>>([]);
  const [score, setScore] = useState<number | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const scanSteps = [
    { text: "→ Initializing Fire Crow Agent Orchestrator...", type: "info" },
    { text: "→ Connecting repository: ", type: "info", appendInput: true },
    { text: "✓ Repository cloned. 47 source files detected.", type: "success" },
    { text: "→ Spawning SAST scanning agent...", type: "info" },
    { text: "! Hardcoded secret found: config.py:16", type: "error" },
    { text: "→ Running dependency audit (OSV-Scanner)...", type: "info" },
    { text: "! CVE-2023-45857: Axios < 1.6.0 (High severity RCE)", type: "warning" },
    { text: "→ Initializing sandbox container...", type: "info" },
    { text: "✓ Dynamic attack simulations: 0 SSRF, 0 IDOR detected.", type: "success" },
    { text: "→ Running AI Analyzer & CVSS scoring...", type: "info" },
    { text: "✓ Verification complete. Remediation report generated.", type: "success" }
  ] as const;

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const startDemoScan = (e: React.FormEvent) => {
    e.preventDefault();
    if (isScanning) return;

    setIsScanning(true);
    setScanStep(0);
    setLogs([]);
    setScore(null);

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < scanSteps.length) {
        const step = scanSteps[currentStep];
        const logText = "appendInput" in step && step.appendInput ? `${step.text}${repoInput}` : step.text;
        setLogs((prev) => [...prev, { text: logText, type: step.type }]);
        setScanStep(currentStep + 1);
        currentStep++;
      } else {
        clearInterval(interval);
        setScore(68); // Demo score
        setIsScanning(false);
      }
    }, 1200);
  };

  return (
    <div className={styles.hero} id="platform">
      <div className={styles.heroCopy}>
        <div className={styles.eyebrowContainer}>
          <span className={styles.eyebrow}>Fire Crow · FCv1</span>
          <span className={styles.pulseDot} />
        </div>
        <h1 className={styles.heroTitle}>
          Security audits<br />
          <span className={styles.heroAccent}>that don&apos;t guess.</span>
        </h1>
        <p className={styles.heroBody}>
          Authorization-only agentic scans with evidence-backed findings.
          Connect your GitHub repository and watch our specialized agent network audit and isolate flaws in seconds.
        </p>

        <form onSubmit={startDemoScan} className={styles.scanForm}>
          <input
            type="text"
            value={repoInput}
            onChange={(e) => setRepoInput(e.target.value)}
            placeholder="Enter public GitHub repo URL..."
            className={styles.urlInput}
            disabled={isScanning}
            required
          />
          <button type="submit" className={styles.primaryButton} disabled={isScanning}>
            {isScanning ? "Scanning..." : "Start Demo Audit →"}
          </button>
        </form>

        <div className={styles.heroFootnotes}>
          {["Authorization-only", "Evidence-backed", "Sandbox-first", "Remediation-focused"].map((t) => (
            <span key={t} className={styles.heroFootnote}>{t}</span>
          ))}
        </div>
      </div>

      <div className={styles.simulatorWrapper}>
        <div className={styles.simulator}>
          <div className={styles.simulatorHeader}>
            <div className={styles.simulatorDots}>
              <span className={styles.simulatorDotRed} />
              <span className={styles.simulatorDotAmber} />
              <span className={styles.simulatorDotGreen} />
            </div>
            <span className={styles.simulatorTitle}>interactive agent shell</span>
          </div>

          <div className={styles.simulatorBody}>
            {logs.length === 0 && !isScanning && (
              <div className={styles.terminalPlaceholder}>
                <p className={styles.welcomeText}>Fire Crow Security Intelligence Shell</p>
                <p className={styles.subWelcomeText}>
                  Type a repository URL on the left and click &quot;Start Demo Audit&quot; to witness the automated agent orchestration.
                </p>
                <div className={styles.commandPrompt}>
                  <span className={styles.terminalPrompt}>$</span>
                  <span className={styles.cursor}>_</span>
                </div>
              </div>
            )}

            {logs.map((log, index) => (
              <div key={index} className={`${styles.terminalLine} ${styles[log.type]}`}>
                <span className={styles.terminalPrompt}>$</span>
                <span>{log.text}</span>
              </div>
            ))}

            {isScanning && scanStep < scanSteps.length && (
              <div className={styles.terminalLine}>
                <span className={styles.terminalPrompt}>$</span>
                <span className={styles.cursor}>_</span>
              </div>
            )}
            <div ref={logsEndRef} />
          </div>

          <AnimatePresence>
            {score !== null && (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 15 }}
                className={styles.resultOverlay}
              >
                <div className={styles.scoreContainer}>
                  <div className={styles.scoreDial}>
                    <svg viewBox="0 0 36 36" className={styles.circularChart}>
                      <path
                        className={styles.circleBg}
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <motion.path
                        className={styles.circle}
                        strokeDasharray={`${score}, 100`}
                        initial={{ strokeDasharray: "0, 100" }}
                        animate={{ strokeDasharray: `${score}, 100` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <div className={styles.scoreText}>
                      <h3>{score}</h3>
                      <span>Risk</span>
                    </div>
                  </div>
                  <div className={styles.resultDetails}>
                    <h4>Scan Completed</h4>
                    <p>Found 1 Critical risk and 1 Medium risk vulnerabilities.</p>
                    <button onClick={onEnter} className={styles.viewReportButton}>
                      Get Full Remediation Report
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className={styles.heroMetrics}>
          {[
            ["14", "Agents Active"],
            ["CVSS 3.1", "Standard"],
            ["PDF/HTML", "Remediation"],
            ["0-days", "Fuzzing Engine"]
          ].map(([val, label]) => (
            <div key={label} className={styles.metricCard}>
              <span className={styles.metricValue}>{val}</span>
              <span className={styles.metricLabel}>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
