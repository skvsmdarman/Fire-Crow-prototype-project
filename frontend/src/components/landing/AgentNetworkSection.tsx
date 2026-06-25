"use client";

import { useState } from "react";
import styles from "./AgentNetworkSection.module.css";

interface AuditingModule {
  name: string;
  tag: string;
  desc: string;
  inputs: string[];
  outputs: string[];
}

const modules: AuditingModule[] = [
  {
    name: "Reconnaissance & Mapping",
    tag: "Recon",
    desc: "Analyzes repository structure, source file layout, and maps trust boundaries.",
    inputs: ["Start"],
    outputs: ["Threat Tree"]
  },
  {
    name: "Threat Tree Modeling",
    tag: "Threat Model",
    desc: "Builds automated attack paths and identifies potential ingress points based on project architecture.",
    inputs: ["Recon"],
    outputs: ["SAST", "Dependencies", "Config Audit"]
  },
  {
    name: "Static Analysis (SAST)",
    tag: "SAST & Semgrep",
    desc: "Executes rule-based AST semantic parsing and pattern-matching scanning to locate insecure code patterns.",
    inputs: ["Threat Model"],
    outputs: ["Evidence Log"]
  },
  {
    name: "Dependency Vulnerability Scanner",
    tag: "Dependencies",
    desc: "Correlates package manifests and lockfiles against public OSV and CVE vulnerability databases.",
    inputs: ["Threat Model"],
    outputs: ["Evidence Log"]
  },
  {
    name: "Configuration & Container Audit",
    tag: "Config Audit",
    desc: "Lints Dockerfiles, settings profiles, and IaC templates to flag permission leaks and secure configuration drifts.",
    inputs: ["Threat Model"],
    outputs: ["Evidence Log"]
  },
  {
    name: "Sandboxed Dynamic Verification",
    tag: "Sandbox Execution",
    desc: "Executes isolated container tests inside secure hypervisors to confirm proof-of-concept exploitability.",
    inputs: ["Threat Model"],
    outputs: ["Evidence Log"]
  },
  {
    name: "Evidence Synthesis",
    tag: "Analysis Synthesis",
    desc: "Aggregates, correlates, and filters out false-positives using multi-source cross-verification engines.",
    inputs: ["SAST & Semgrep", "Dependencies", "Config Audit", "Sandbox Execution"],
    outputs: ["Remediation Graph"]
  },
  {
    name: "Remediation & Report Compilation",
    tag: "Reporting",
    desc: "Compiles actionable code-level remediation snippets, verified proof-of-concept evidence, and PDF reports.",
    inputs: ["Remediation Graph"],
    outputs: ["Audit Report"]
  }
];

export default function AgentNetworkSection() {
  const [hoveredModule, setHoveredModule] = useState<AuditingModule | null>(null);

  const getModuleStatus = (mod: AuditingModule) => {
    if (!hoveredModule) return "idle";
    if (hoveredModule.name === mod.name) return "focused";
    if (hoveredModule.outputs.includes(mod.tag) || mod.inputs.includes(hoveredModule.tag)) {
      return "connected";
    }
    return "muted";
  };

  return (
    <section className={styles.section} id="agents">
      <div className={styles.sectionHeader}>
        <div>
          <span className={styles.eyebrow}>Auditing Pipeline</span>
          <h2 className={styles.sectionTitle}>Modular Auditing & Sandbox Verification</h2>
        </div>
        <p className={styles.sectionIntro}>
          Fire Crow coordinates multiple specialized auditing modules to scanning repository targets. Hover over any module below to trace its data inputs and outputs in the orchestration pipeline.
        </p>
      </div>

      <div className={styles.grid}>
        {modules.map((mod) => {
          const status = getModuleStatus(mod);
          return (
            <div
              key={mod.name}
              className={`${styles.card} ${styles[status]}`}
              onMouseEnter={() => setHoveredModule(mod)}
              onMouseLeave={() => setHoveredModule(null)}
            >
              <div className={styles.cardHeader}>
                <span className={styles.tag}>{mod.tag}</span>
              </div>
              <h3 className={styles.title}>{mod.name}</h3>
              <p className={styles.desc}>{mod.desc}</p>
              
              <div className={styles.metrics}>
                {status === "focused" && (
                  <div className={styles.connections}>
                    {mod.inputs[0] !== "Start" && (
                      <div className={styles.conn}>
                        <span className={styles.connLabel}>Inputs:</span>
                        <span className={styles.connVal}>{mod.inputs.join(", ")}</span>
                      </div>
                    )}
                    {mod.outputs[0] !== "Audit Report" && (
                      <div className={styles.conn}>
                        <span className={styles.connLabel}>Outputs:</span>
                        <span className={styles.connVal}>{mod.outputs.join(", ")}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
