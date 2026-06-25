"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import styles from "./HeroSection.module.css";
import { usePolicyContext } from "../../features/auth/hooks";
import { detectRegionFromTimezone } from "../../lib/policyData";
import { buildApiUrl } from "../../shared/api/baseUrl";

interface HeroSectionProps {
  onEnter: () => void;
}

const DEFAULT_REPO = "github.com/acme/backend-api";

export default function HeroSection({ onEnter }: HeroSectionProps) {
  const [repoInput, setRepoInput] = useState(DEFAULT_REPO);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [logs, setLogs] = useState<Array<{ text: string; type: "info" | "success" | "warning" | "error" }>>([]);
  const [score, setScore] = useState<number | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  const { activePrivacyVersion, providerAvailability } = usePolicyContext();

  const getOauthHref = (provider: "github" | "google") => {
    let authUrl = buildApiUrl(`/auth/${provider}?privacy_policy_accepted=true&privacy_policy_version=${activePrivacyVersion}`);
    if (typeof window !== "undefined") {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      authUrl += `&timezone=${encodeURIComponent(tz)}&region=${encodeURIComponent(detectRegionFromTimezone(tz))}`;
    }
    return authUrl;
  };

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
    if (isScanning && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, isScanning]);

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

  // Framer Motion Animation Settings
  const titleContainerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] } }
  };

  return (
    <div className={styles.hero} id="platform">
      <motion.div 
        className={styles.heroCopy}
        variants={titleContainerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={itemVariants} className={styles.eyebrowContainer}>
          <span className={styles.eyebrow}>Fire Crow · FCv1</span>
          <span className={styles.pulseDot} />
        </motion.div>
        
        <motion.h1 variants={itemVariants} className={styles.heroTitle}>
          Security audits<br />
          <span className={styles.heroAccent}>that don&apos;t guess.</span>
        </motion.h1>
        
        <motion.p variants={itemVariants} className={styles.heroBody}>
          Authorization-only agentic scans with evidence-backed findings.
          Connect your GitHub repository and watch our specialized agent network audit and isolate flaws in seconds.
        </motion.p>

        <motion.form variants={itemVariants} onSubmit={startDemoScan} className={styles.scanForm}>
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
        </motion.form>

        {/* Direct Google & GitHub login options */}
        <motion.div variants={itemVariants} className={styles.directLoginSection}>
          <div className={styles.divider}>
            <span className={styles.dividerLine} />
            <span className={styles.dividerText}>or audit your private repositories</span>
            <span className={styles.dividerLine} />
          </div>
          <div className={styles.heroOauth}>
            {providerAvailability.github && (
              <a href={getOauthHref("github")} className={styles.heroOauthButton}>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" className={styles.oauthIcon}>
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                <span>Start with GitHub</span>
              </a>
            )}
            {providerAvailability.google && (
              <a href={getOauthHref("google")} className={`${styles.heroOauthButton} ${styles.google}`}>
                <svg viewBox="0 0 24 24" width="16" height="16" className={styles.oauthIcon}>
                  <path fill="#EA4335" d="M12 5.04c1.66 0 3.2.57 4.38 1.69l3.27-3.27C17.67 1.54 14.98 0 12 0 7.35 0 3.37 2.67 1.39 6.56l3.87 3a7.18 7.18 0 0 1 6.74-4.52z"/>
                  <path fill="#4285F4" d="M23.49 12.27c0-.81-.07-1.59-.2-2.36H12v4.51h6.43a5.5 5.5 0 0 1-2.39 3.61l3.71 2.88c2.17-2 3.74-4.94 3.74-8.64z"/>
                  <path fill="#FBBC05" d="M5.26 14.12a7.15 7.15 0 0 1 0-4.24l-3.87-3a11.96 11.96 0 0 0 0 10.24l3.87-3z"/>
                  <path fill="#34A853" d="M12 24c3.24 0 5.97-1.07 7.96-2.91l-3.71-2.88a7.14 7.14 0 0 1-10.99-3.69l-3.87 3C3.37 21.33 7.35 24 12 24z"/>
                </svg>
                <span>Start with Google</span>
              </a>
            )}
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className={styles.heroFootnotes}>
          {["Authorization-only", "Evidence-backed", "Sandbox-first", "Remediation-focused"].map((t) => (
            <span key={t} className={styles.heroFootnote}>{t}</span>
          ))}
        </motion.div>
      </motion.div>

      <motion.div 
        className={styles.simulatorWrapper}
        initial={{ opacity: 0, y: 30, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1], delay: 0.4 }}
      >
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
            ["Docker", "Sandbox Verification"],
            ["CVSS 3.1", "Standard"],
            ["PDF/HTML", "Remediation"],
            ["Git", "Integration"]
          ].map(([val, label]) => (
            <div key={label} className={styles.metricCard}>
              <span className={styles.metricValue}>{val}</span>
              <span className={styles.metricLabel}>{label}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
