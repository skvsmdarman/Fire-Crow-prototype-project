"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { COMPANY_NAME, PRODUCT_VERSION, COPYRIGHT_YEAR, PRODUCT_TAGLINE } from "../../shared/config/app";
import styles from "./page.module.css";

export default function AgentsPage() {
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
            <Link href="/agents" className={`${styles.navLink} ${styles.navLinkActive}`}>
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
            <p className={styles.eyebrow}>Fire Crow · Modules</p>
            <h1 className={styles.heroTitle}>
              Security Auditing<br />
              <span className={styles.heroAccent}>Pipeline Modules</span>
            </h1>
            <p className={styles.heroBody}>
              Our security auditing lifecycle is broken down into specialized modules,
              working sequentially to deliver comprehensive and verifiable protection.
            </p>

            <div className={styles.heroActions}>
              <Link href="/dashboard" className={styles.primaryButton}>
                Open Dashboard
              </Link>
              <Link href="/workflow" className={styles.secondaryButton}>
                View Workflow
              </Link>
            </div>

            <div className={styles.heroFootnotes}>
              {["Modular", "Coordinated", "Evidence-Based", "Continuous"].map((t) => (
                <span key={t} className={styles.heroFootnote}>{t}</span>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Agent Grid */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Auditing Pipeline</p>
              <h2 className={styles.sectionTitle}>Pipeline Analysis<br />Modules</h2>
            </div>
            <p className={styles.sectionIntro}>
              Our analysis pipeline runs multiple security modules, each responsible
              for a specific aspect of security testing, coordinated sequentially to produce
              verifiable, evidence-backed security findings.
            </p>
          </div>
          <div className={styles.agentGrid}>
            {[
              ["Recon", "Subdomain, tech fingerprinting, and public-facing endpoint discovery"],
              ["Threat Model", "Attack tree generation, trust boundary analysis, and asset mapping"],
              ["SAST", "Static analysis using pattern-matching abstract syntax tree (AST) scanners"],
              ["Semgrep", "Deep semantic rule matching to find semantic and syntax logic bugs"],
              ["Dependency", "OSV-scanner vulnerability correlation and package manifest checks"],
              ["IaC Scanner", "Infrastructure-as-Code audits for Terraform, Kubernetes, and CloudFormation"],
              ["Config Scan", "Dockerfile, Hadolint, and deployment profile linting"],
              ["Dynamic Attack", "Sandboxed simulations for SSRF, rate limit bypasses, and JWT spoofing"],
              ["Authz/IDOR", "Privilege boundary and access control verification in sandbox"],
              ["Container Scan", "Base image vulnerability and software layer integrity scanning"],
              ["SBOM Graph", "Software Bill-of-Materials dependency graph generation"],
              ["AI Analyzer", "Evidence-backed correlation to cross-reference multiple findings"],
              ["Cross-Validation", "False positive filtering and deduplication of scan records"],
              ["Remediation", "Compilation of actionable, code-level fix recommendations"],
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
            <p className={styles.eyebrow}>Experience comprehensive security</p>
            <h2 className={styles.ctaTitle}>Run your first audit</h2>
            <p className={styles.ctaCopy}>
              Leverage our complete auditing pipeline to secure your repositories with
              evidence-backed findings and actionable remediation guidance.
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
