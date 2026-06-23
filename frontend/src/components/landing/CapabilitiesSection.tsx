"use client";

import { motion } from "framer-motion";
import styles from "./CapabilitiesSection.module.css";

const capabilities = [
  {
    title: "SAST & Semgrep",
    short: "SAST",
    desc: "Pattern-based vulnerability detection across 40+ languages and frameworks, identifying injection flaws, poor sanitization, and structural risks.",
    color: "var(--orange)",
    icon: (
      <svg className={styles.icon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v1" />
        <path d="M18 8h4a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-4" />
        <line x1="8" y1="10" x2="8" y2="14" />
        <line x1="5" y1="12" x2="11" y2="12" />
      </svg>
    )
  },
  {
    title: "Dependency Audit",
    short: "Supply Chain",
    desc: "Integrates directly with OSV-scanner databases to verify package manifests, transitive dependencies, and container layers for known CVEs.",
    color: "var(--blue)",
    icon: (
      <svg className={styles.icon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
      </svg>
    )
  },
  {
    title: "IaC & Config Scan",
    short: "Infrastructure",
    desc: "Infrastructure-as-code linting and audits for Terraform templates, Kubernetes manifests, and Dockerfiles to prevent deployment misconfigurations.",
    color: "var(--amber)",
    icon: (
      <svg className={styles.icon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="9" y1="3" x2="9" y2="21" />
        <line x1="15" y1="3" x2="15" y2="21" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="3" y1="15" x2="21" y2="15" />
      </svg>
    )
  },
  {
    title: "Dynamic Attack",
    short: "DAST Sandbox",
    desc: "Validates code pathways in secure isolated sandboxes, checking for rate limits, server-side request forgery (SSRF), IDOR, and session issues.",
    color: "var(--green)",
    icon: (
      <svg className={styles.icon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    )
  }
];

export default function CapabilitiesSection() {
  return (
    <section className={styles.section} id="capabilities">
      <div className={styles.sectionHeader}>
        <div>
          <span className={styles.eyebrow}>Capabilities</span>
          <h2 className={styles.sectionTitle}>Full-spectrum security analysis</h2>
        </div>
        <p className={styles.sectionIntro}>
          From static analysis to dynamic sandbox execution. Our orchestrator splits workloads across multiple sandboxed execution layers to secure every entry point.
        </p>
      </div>

      <div className={styles.grid}>
        {capabilities.map((c, i) => (
          <motion.div
            key={c.title}
            className={styles.card}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            whileHover={{ y: -5 }}
            style={{ "--accent-color": c.color } as React.CSSProperties}
          >
            <div className={styles.cardHeader}>
              <span className={styles.cardTag}>{c.short}</span>
              <div className={styles.iconContainer}>{c.icon}</div>
            </div>
            <h3 className={styles.cardTitle}>{c.title}</h3>
            <p className={styles.cardDesc}>{c.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
