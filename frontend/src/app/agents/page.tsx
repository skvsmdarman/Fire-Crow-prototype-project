"use client";

import { useState, useEffect } from "react";
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
              Agents
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
            <p className={styles.eyebrow}>Fire Crow · Agents</p>
            <h1 className={styles.heroTitle}>
              14 Specialized<br />
              <span className={styles.heroAccent}>Security Agents</span>
            </h1>
            <p className={styles.heroBody}>
              Each agent handles a specific phase of the security audit lifecycle,
              working together to deliver comprehensive protection.
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
              {["Specialized", "Coordinated", "Evidence-Based", "Continuous"].map((t) => (
                <span key={t} className={styles.heroFootnote}>{t}</span>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Agent Grid */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Agent Network</p>
              <h2 className={styles.sectionTitle}>Specialized Security< br />Agents</h2>
            </div>
            <p className={styles.sectionIntro}>
              Our agent network consists of 14 specialized agents, each responsible
              for a specific aspect of security testing, coordinated by our 
              LangGraph-based orchestration engine.
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
            <p className={styles.eyebrow}>Experience comprehensive security</p>
            <h2 className={styles.ctaTitle}>Run your first audit</h2>
            <p className={styles.ctaCopy}>
              Leverage our full agent network to secure your repositories with
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
