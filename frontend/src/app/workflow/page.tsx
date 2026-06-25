"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { COMPANY_NAME, PRODUCT_VERSION, COPYRIGHT_YEAR, PRODUCT_TAGLINE } from "../../shared/config/app";
import styles from "./page.module.css";

const TONE = {
  muted: "#5b6880",
  green: "#00e676",
  red: "#ff3047",
  amber: "#ffb800",
};

export default function WorkflowPage() {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setTick((p) => p + 1), 2000);
    return () => clearInterval(t);
  }, []);

  const termLines = [
    { txt: "→ Initializing Fire Crow pipeline orchestrator", tone: TONE.muted },
    { txt: "✓ Orchestrator engine initialized", tone: TONE.green },
    { txt: "→ Loading security pipeline modules", tone: TONE.muted },
    { txt: "✓ Recon module: Subdomain & tech fingerprinting", tone: TONE.green },
    { txt: "✓ Threat Model module: Attack surface mapping", tone: TONE.green },
    { txt: "✓ SAST module: AST code pattern scanning", tone: TONE.green },
    { txt: "✓ Semgrep module: Custom rule-based deep inspection", tone: TONE.green },
    { txt: "✓ Dependency module: OSV-scanner CVE correlation", tone: TONE.green },
    { txt: "✓ IaC Scanner module: Terraform/K8s/Dockerfile audit", tone: TONE.green },
    { txt: "✓ Config Scan module: hadolint/kube-linter/tfsec", tone: TONE.green },
    { txt: "✓ Dynamic Attack module: Sandboxed exploit validation", tone: TONE.green },
    { txt: "✓ Authz/IDOR module: Privilege escalation testing", tone: TONE.green },
    { txt: "✓ Container Scan module: Image vulnerability scanning", tone: TONE.green },
    { txt: "✓ SBOM Graph module: Software bill-of-materials", tone: TONE.green },
    { txt: "✓ AI Analyzer module: Evidence correlation engine", tone: TONE.green },
    { txt: "✓ Cross-Validation module: False positive detection", tone: TONE.green },
    { txt: "✓ Remediation module: Fix recommendation engine", tone: TONE.green },
    { txt: "→ Orchestrator ready for audit execution", tone: TONE.muted },
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
            <Link href="/workflow" className={`${styles.navLink} ${styles.navLinkActive}`}>
              Workflow
            </Link>
            <Link href="/agents" className={styles.navLink}>
              Modules
            </Link>
          </div>
        </nav>

        {/* Hero */}
        <div className={styles.hero}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className={styles.heroCopy}
          >
            <p className={styles.eyebrow}>Fire Crow · Workflow</p>
            <h1 className={styles.heroTitle}>
              Automated Security Audit<br />
              <span className={styles.heroAccent}>Pipeline in Action</span>
            </h1>
            <p className={styles.heroBody}>
              Specialized analysis modules orchestrated sequentially
              to deliver comprehensive, evidence-backed security assessments.
            </p>

            <div className={styles.heroActions}>
              <Link href="/dashboard" className={styles.primaryButton}>
                Open Dashboard
              </Link>
              <Link href="/agents" className={styles.secondaryButton}>
                View Modules
              </Link>
            </div>

            <div className={styles.heroFootnotes}>
              {["Orchestrated", "Evidence-Based", "Authorization-First", "Remediation-Ready"].map((t) => (
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
                <span className={styles.simulatorTitle}>firecrow · workflow orchestrator</span>
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
              {[["Modular", "Pipeline"], ["Strict", "Orchestration"], ["Sandbox", "Dynamic Testing"], ["Evidence", "Backed"]].map(([v, l]) => (
                <div key={l} className={styles.metricCard}>
                  <span className={styles.metricValue}>{v}</span>
                  <span className={styles.metricLabel}>{l}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Workflow Details */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>How It Works</p>
              <h2 className={styles.sectionTitle}>The Fire Crow<br />Security Audit Pipeline</h2>
            </div>
            <p className={styles.sectionIntro}>
              Our analysis pipeline transforms raw code into actionable security intelligence
              through coordinated module execution and evidence validation.
            </p>
          </div>
          <div className={styles.workflowSteps}>
            {[
              {
                step: 1,
                title: "Repository Ingestion",
                desc: "Securely clone and prepare the target repository for analysis",
                icon: "⬇️",
                active: true,
              },
              {
                step: 2,
                title: "Reconnaissance",
                desc: "Discover subdomains, endpoints, and technology stack",
                icon: "🔍",
                active: true,
              },
              {
                step: 3,
                title: "Threat Modeling",
                desc: "Map attack surface and generate asset inventory",
                icon: "🎯",
                active: true,
              },
              {
                step: 4,
                title: "Static Analysis",
                desc: "Run SAST, Semgrep, and dependency scans",
                icon: "📊",
                active: true,
              },
              {
                step: 5,
                title: "Configuration Audit",
                desc: "Validate IaC, container, and config security",
                icon: "⚙️",
                active: true,
              },
              {
                step: 6,
                title: "Dynamic Testing",
                desc: "Execute sandboxed exploit validation",
                icon: "💥",
                active: true,
              },
              {
                step: 7,
                title: "Access Control Testing",
                desc: "Test for authorization bypass and IDOR vulnerabilities",
                icon: "🔐",
                active: true,
              },
              {
                step: 8,
                title: "Evidence Correlation",
                desc: "Cross-validate findings and eliminate false positives",
                icon: "🔗",
                active: true,
              },
              {
                step: 9,
                title: "Risk Scoring",
                desc: "Apply CVSS 3.1 scoring and business context",
                icon: "📈",
                active: true,
              },
              {
                step: 10,
                title: "Report Generation",
                desc: "Create evidence-backed remediation report",
                icon: "📄",
                active: true,
              },
            ].map((step) => (
              <div key={step.step} className={styles.workflowStep}>
                <div className={styles.workflowStepNumber}>
                  {step.step}
                </div>
                <div className={styles.workflowStepContent}>
                  <div className={styles.workflowStepIcon}>{step.icon}</div>
                  <div>
                    <h3>{step.title}</h3>
                    <p>{step.desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className={styles.cta}>
          <div className={styles.ctaContent}>
            <p className={styles.eyebrow}>Ready to see it in action?</p>
            <h2 className={styles.ctaTitle}>Start your first security audit</h2>
            <p className={styles.ctaCopy}>
              Connect your repository and watch our pipeline modules perform a comprehensive
              security assessment in real-time.
            </p>
            <div className={styles.heroActions} style={{ marginTop: 20 }}>
              <Link href="/dashboard" className={styles.launchButton}>
                Start an audit →
              </Link>
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