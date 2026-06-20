"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  getServerAuthSessionSnapshot,
  getStoredAuthSessionSnapshot,
  subscribeToAuthSession,
} from "../lib/authSession";
import { COMPANY_NAME, PRODUCT_VERSION, COPYRIGHT_YEAR, PRODUCT_TAGLINE } from "../shared/config/app";
import styles from "./page.module.css";

const TONE = {
  muted: "#5b6880",
  green: "#00e676",
  red: "#ff3047",
  amber: "#ffb800",
};

export default function LandingPage() {
  const router = useRouter();
  const session = useSyncExternalStore(
    subscribeToAuthSession,
    getStoredAuthSessionSnapshot,
    getServerAuthSessionSnapshot
  );
  const isLoggedIn = session.hasDashboardSession;

  const [tick, setTick] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setTick((p) => p + 1), 2000);
    return () => clearInterval(t);
  }, []);

  const handleEnter = () => {
    router.push(isLoggedIn ? "/dashboard" : "/signin");
  };

  const termLines = [
    { txt: "→ cloning acme/backend-api@main", tone: TONE.muted },
    { txt: "✓ SAST scan complete — 47 patterns checked", tone: TONE.green },
    { txt: "! hardcoded secret detected at config.py:16", tone: TONE.red },
    { txt: "→ running dependency audit (osv-scanner)", tone: TONE.muted },
    { txt: "! CVE-2021-23337 lodash@4.17.15", tone: TONE.amber },
    { txt: "✓ CVSS scoring complete — max 9.8", tone: TONE.green },
    { txt: "→ generating report", tone: TONE.muted },
  ];
  const visible = termLines.slice(0, Math.min(tick + 1, termLines.length));

  return (
    <div className={styles.page}>
      <div className={styles.backdrop} />
      <div className={styles.noise} />
      <div className={styles.container}>
        {/* Nav */}
        <nav className={styles.nav}>
          <Link href="/" className={styles.brand}>
            <span className={styles.brandMark}>FC</span>
            <span className={styles.brandText}>
              <strong>Fire Crow</strong>
              <small>{PRODUCT_TAGLINE}</small>
            </span>
          </Link>
          <div className={styles.navLinks}>
            <Link href="/" className={styles.navLink}>
              Platform
            </Link>
            <Link href="/workflow" className={styles.navLink}>
              Workflow
            </Link>
            <Link href="/agents" className={styles.navLink}>
              Agents
            </Link>
            <button onClick={handleEnter} className={styles.navCta}>
              {isLoggedIn ? "Dashboard" : "Sign in"}
            </button>
          </div>
        </nav>

        {/* Hero */}
        <div className={styles.hero} id="platform">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className={styles.heroCopy}
          >
            <p className={styles.eyebrow}>Fire Crow · FCv1</p>
            <h1 className={styles.heroTitle}>
              Security audits<br />
              <span className={styles.heroAccent}>that don&apos;t guess.</span>
            </h1>
            <p className={styles.heroBody}>
              Authorization-only agentic scans with evidence-backed findings.
              Connect a repository and receive a remediation-ready report in minutes.
            </p>

            <div className={styles.heroActions}>
              <button onClick={handleEnter} className={styles.primaryButton}>
                {isLoggedIn ? "Open Dashboard" : "Start an audit →"}
              </button>
              <button onClick={() => router.push("/workflow")} className={styles.secondaryButton}>View workflow</button>
            </div>

            <div className={styles.heroFootnotes}>
              {["Authorization-only", "Evidence-backed", "Sandbox-first", "Remediation-focused"].map((t) => (
                <span key={t} className={styles.heroFootnote}>{t}</span>
              ))}
            </div>
          </motion.div>

          {/* Terminal & metrics */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
          >
            <div className={styles.simulator}>
              <div className={styles.simulatorHeader}>
                <div className={styles.simulatorDots}>
                  <span className={styles.simulatorDotRed} />
                  <span className={styles.simulatorDotAmber} />
                  <span className={styles.simulatorDotGreen} />
                </div>
                <span className={styles.simulatorTitle}>firecrow · scan output</span>
              </div>
              <div className={styles.simulatorBody}>
                {visible.map((l, i) => (
                  <div key={i} className={styles.terminalLine}>
                    <span className={styles.terminalPrompt}>$</span>
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className={styles.terminalText}
                      style={{ color: l.tone }}
                    >
                      {l.txt}
                    </motion.span>
                  </div>
                ))}
                {visible.length < termLines.length && (
                  <div className={styles.terminalLine}>
                    <span className={styles.terminalPrompt}>$</span>
                    <span className={styles.terminalText}>_</span>
                  </div>
                )}
              </div>
            </div>

            <div className={styles.heroMetrics}>
              {[["14", "Agents"], ["CVSS 3.1", "Scoring"], ["PDF", "Reports"], ["0-days", "Detection"]].map(([v, l]) => (
                <div key={l} className={styles.metricCard}>
                  <span className={styles.metricValue}>{v}</span>
                  <span className={styles.metricLabel}>{l}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Capabilities */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Capabilities</p>
              <h2 className={styles.sectionTitle}>Full-spectrum< br />security analysis</h2>
            </div>
            <p className={styles.sectionIntro}>
              From static analysis to dynamic sandbox evaluation — our agent network
              covers every attack surface your codebase exposes.
            </p>
          </div>
          <div className={styles.capabilityGrid}>
            {[
              ["SAST & Semgrep", "Pattern-based vulnerability detection across 40+ languages and frameworks."],
              ["Dependency Audit", "OSV-scanner integration checks your supply chain for known CVEs."],
              ["IaC & Config Scan", "Terraform, K8s, Dockerfile, and cloud security posture validation."],
              ["Dynamic Attack", "Sandboxed SSRF, XXE, SSTI, JWT tampering, and rate-limit testing."],
            ].map(([title, desc]) => (
              <div key={title} className={styles.capabilityCard}>
                <span className={styles.capabilityMeta}>{title.split(" ")[0]}</span>
                <h3>{title}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline Demo */}
        <div className={`${styles.section} ${styles.demoSection}`}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Pipeline</p>
              <h2 className={styles.sectionTitle}>Agentic pipeline< br />in motion</h2>
            </div>
            <p className={styles.sectionIntro}>
              14 specialized agents orchestrate end-to-end, from reconnaissance
              to remediation reporting.
            </p>
          </div>
          <div className={styles.demoSplit}>
            <div className={styles.pipelinePanel}>
              {[
                { name: "Reconnaissance", desc: "Subdomain, endpoint, and technology fingerprinting", active: true },
                { name: "Threat Modeling", desc: "Asset enumeration and attack surface mapping", done: true },
                { name: "SAST Analysis", desc: "ESLint + Bandit pattern matching", done: true },
                { name: "Dependency Scan", desc: "OSV and CVE database correlation", active: true },
                { name: "Dynamic Attack", desc: "Sandboxed exploit validation", done: false },
              ].map((step, i) => (
                <div
                  key={step.name}
                  className={`${styles.pipelineCard} ${step.active ? styles.pipelineCardActive : ""} ${step.done ? styles.pipelineCardDone : ""}`}
                >
                  <div className={styles.pipelineHeader}>
                    <strong>Step {i + 1}</strong>
                    <span style={{
                      color: step.done ? "#00e676" : step.active ? "#ff7200" : "#3a4358",
                      fontSize: 11,
                    }}>
                      {step.done ? "✓ Done" : step.active ? "● Running" : "Pending"}
                    </span>
                  </div>
                  <h3>{step.name}</h3>
                  <p>{step.desc}</p>
                </div>
              ))}
            </div>

            {/* Hero Board */}
            <div className={styles.heroBoard}>
              <div className={styles.boardHeader}>
                <div>
                  <p className={styles.boardLabel}>Current scan</p>
                  <h3 className={styles.boardTitle}>acme/backend-api</h3>
                </div>
                <span className={styles.boardBadge}>CVSS 9.8</span>
              </div>
              <div className={styles.boardList}>
                {[
                  ["01", "Hardcoded Secret", "AWS key detected in config.py:16", "Critical"],
                  ["02", "SQL Injection", "Raw query concatenation in users.py:204", "High"],
                  ["03", "CVE-2021-23337", "lodash@4.17.15 known RCE", "High"],
                  ["04", "JWT Weak Secret", "Hardcoded 'secret' in auth middleware", "Medium"],
                ].map(([idx, title, desc, severity]) => (
                  <div key={idx} className={styles.boardItem}>
                    <span className={styles.boardIndex}>{idx}</span>
                    <div className={styles.boardBody}>
                      <strong>{title}</strong>
                      <span>{desc}</span>
                    </div>
                    <span className={`${styles.boardState} ${styles[`severity${severity}`] || ""}`}>{severity}</span>
                  </div>
                ))}
              </div>
              <div className={styles.boardFooter}>
                <div>
                  <span className={styles.boardFooterLabel}>Attack graph</span>
                  <p className={styles.boardFooterValue}>
                    Cross-contamination path: secret → lateral movement → data exfiltration
                  </p>
                </div>
                <button onClick={handleEnter} className={styles.boardFooterLink}>Full report →</button>
              </div>
            </div>
          </div>
        </div>

        {/* Agent Network */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Agent Network</p>
              <h2 className={styles.sectionTitle}>14 specialized< br />security agents</h2>
            </div>
            <p className={styles.sectionIntro}>
              Each agent handles a specific phase of the audit lifecycle,
              coordinated by our LangGraph-based maestro.
            </p>
          </div>
          <div className={styles.agentGrid}>
            {[
              ["Recon", "Subdomain, tech fingerprinting, endpoint discovery"],
              ["Threat Model", "Attack tree generation and asset mapping"],
              ["SAST", "Static analysis with Bandit + ESLint"],
              ["Semgrep", "Custom rule-based deep code inspection"],
              ["Dependency", "OSV-scanner CVE correlation"],
              ["IaC Scanner", "Terraform, K8s, Dockerfile audits"],
              ["Config Scan", "hadolint, kube-linter, tfsec"],
              ["Dynamic Attack", "Sandboxed SSRF, XXE, SSTI, JWT, rate limit"],
              ["Authz/IDOR", "Access control and privilege analysis"],
              ["Container Scan", "Docker image vulnerability scanning"],
              ["SBOM Graph", "Software bill-of-materials graph builder"],
              ["AI Analyzer", "LLM-based evidence correlation"],
              ["Cross-Validation", "False positive detection and dedup"],
              ["Remediation", "Actionable fix recommendation engine"],
            ].map(([name, desc]) => (
              <div key={name} className={styles.agentCard}>
                <div className={styles.agentHeader}>
                  <span className={styles.agentTag}>{name}</span>
                </div>
                <h3>{name}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className={styles.cta}>
          <div className={styles.ctaContent}>
            <p className={styles.eyebrow}>Get started</p>
            <h2 className={styles.ctaTitle}>Ready to secure your repository?</h2>
            <p className={styles.ctaCopy}>
              Connect your codebase and receive a comprehensive, evidence-backed
              security assessment within minutes.
            </p>
            <div className={styles.heroActions} style={{ marginTop: 20 }}>
              <button onClick={handleEnter} className={styles.launchButton}>
                {isLoggedIn ? "Go to Dashboard" : "Start an audit →"}
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className={styles.footer}>
          <div className={styles.footerBrand}>
            <Link href="/" className={styles.brand}>
              <span className={styles.brandMark}>FC</span>
              <span className={styles.brandText}>
                <strong>Fire Crow</strong>
                <small>{PRODUCT_TAGLINE}</small>
              </span>
            </Link>
            <p>Authorization-only security audit platform for SaaS repositories.</p>
          </div>
          <div className={styles.footerLinks}>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>
              © {COPYRIGHT_YEAR} {COMPANY_NAME} · Fire Crow {PRODUCT_VERSION}
            </span>
            <Link href="/privacy">Privacy</Link>
            <Link href="/terms">Terms</Link>
          </div>
        </footer>
      </div>
    </div>
  );
}
