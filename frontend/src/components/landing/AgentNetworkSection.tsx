"use client";

import { useState } from "react";
import styles from "./AgentNetworkSection.module.css";

interface Agent {
  name: string;
  tag: string;
  desc: string;
  accuracy: string;
  speed: string;
  inputs: string[];
  outputs: string[];
}

const agents: Agent[] = [
  {
    name: "Recon Agent",
    tag: "Recon",
    desc: "Performs subdomain discovery, technology fingerprinting, and public-facing endpoint identification.",
    accuracy: "98.7%",
    speed: "1.8s",
    inputs: ["Start"],
    outputs: ["Threat Model"]
  },
  {
    name: "Threat Model Agent",
    tag: "Threat Model",
    desc: "Builds automated attack trees, entry points, and trust-boundary graphs based on repo anatomy.",
    accuracy: "95.2%",
    speed: "2.4s",
    inputs: ["Recon"],
    outputs: ["SAST", "Semgrep", "IaC Scanner", "Config Scan"]
  },
  {
    name: "SAST Agent",
    tag: "SAST",
    desc: "Executes lightweight pattern-matching AST scans to locate common vulnerability structures.",
    accuracy: "91.5%",
    speed: "1.2s",
    inputs: ["Threat Model"],
    outputs: ["AI Analyzer"]
  },
  {
    name: "Semgrep Agent",
    tag: "Semgrep",
    desc: "Performs deep semantic rule matching to find semantic and syntax logic bugs.",
    accuracy: "96.1%",
    speed: "2.1s",
    inputs: ["Threat Model"],
    outputs: ["AI Analyzer"]
  },
  {
    name: "Dependency Agent",
    tag: "Dependency",
    desc: "Correlates package manifests and transitive dependencies against OSV and CVE registries.",
    accuracy: "99.9%",
    speed: "0.8s",
    inputs: ["Threat Model"],
    outputs: ["SBOM Graph"]
  },
  {
    name: "IaC Scanner Agent",
    tag: "IaC Scanner",
    desc: "Audits Terraform templates, CloudFormation, and Kubernetes manifests for structural leaks.",
    accuracy: "97.4%",
    speed: "1.5s",
    inputs: ["Threat Model"],
    outputs: ["Container Scan"]
  },
  {
    name: "Config Scan Agent",
    tag: "Config Scan",
    desc: "Lints Dockerfiles, hadolint files, and local settings profiles to flag configuration drifts.",
    accuracy: "98.2%",
    speed: "1.1s",
    inputs: ["Threat Model"],
    outputs: ["Container Scan"]
  },
  {
    name: "Dynamic Attack Agent",
    tag: "Dynamic Attack",
    desc: "Simulates Rate Limiting, SSRF, XXE, and session spoofing attempts inside secure sandboxes.",
    accuracy: "99.1%",
    speed: "4.8s",
    inputs: ["Threat Model"],
    outputs: ["Authz/IDOR", "AI Analyzer"]
  },
  {
    name: "Authz/IDOR Agent",
    tag: "Authz/IDOR",
    desc: "Validates access control matrices, authentication bounds, and IDOR vectors inside sandbox tests.",
    accuracy: "94.6%",
    speed: "3.5s",
    inputs: ["Dynamic Attack"],
    outputs: ["AI Analyzer"]
  },
  {
    name: "Container Scan Agent",
    tag: "Container Scan",
    desc: "Audits base images, system dependencies, and runtime layer integrity in sandbox hosts.",
    accuracy: "99.3%",
    speed: "2.9s",
    inputs: ["IaC Scanner", "Config Scan"],
    outputs: ["AI Analyzer"]
  },
  {
    name: "SBOM Graph Agent",
    tag: "SBOM Graph",
    desc: "Generates fully mapped software bills-of-material dependencies graphs and dependency relations.",
    accuracy: "100%",
    speed: "1.4s",
    inputs: ["Dependency"],
    outputs: ["AI Analyzer"]
  },
  {
    name: "AI Analyzer Agent",
    tag: "AI Analyzer",
    desc: "Performs LLM-guided evidence correlation and multi-agent synthesis to cross-verify logs.",
    accuracy: "97.8%",
    speed: "5.2s",
    inputs: ["SAST", "Semgrep", "Authz/IDOR", "Container Scan", "SBOM Graph"],
    outputs: ["Cross-Validation"]
  },
  {
    name: "Cross-Validation Agent",
    tag: "Validation",
    desc: "Filters out false positives and deduplicates findings based on historical execution metrics.",
    accuracy: "99.5%",
    speed: "1.6s",
    inputs: ["AI Analyzer"],
    outputs: ["Remediation"]
  },
  {
    name: "Remediation Agent",
    tag: "Remediation",
    desc: "Compiles executable patching code blocks, remediation files, and final audit summaries.",
    accuracy: "96.8%",
    speed: "3.2s",
    inputs: ["Cross-Validation"],
    outputs: ["Report"]
  }
];

export default function AgentNetworkSection() {
  const [hoveredAgent, setHoveredAgent] = useState<Agent | null>(null);

  const getAgentStatus = (agent: Agent) => {
    if (!hoveredAgent) return "idle";
    if (hoveredAgent.name === agent.name) return "focused";
    if (hoveredAgent.outputs.includes(agent.tag) || agent.inputs.includes(hoveredAgent.tag)) {
      return "connected";
    }
    return "muted";
  };

  return (
    <section className={styles.section} id="agents">
      <div className={styles.sectionHeader}>
        <div>
          <span className={styles.eyebrow}>Agent Network</span>
          <h2 className={styles.sectionTitle}>14 specialized security agents</h2>
        </div>
        <p className={styles.sectionIntro}>
          Coordinated by a LangGraph maestro. Hover over any agent below to trace its data inputs, outputs, and performance metrics in the orchestration pipeline.
        </p>
      </div>

      <div className={styles.grid}>
        {agents.map((agent) => {
          const status = getAgentStatus(agent);
          return (
            <div
              key={agent.name}
              className={`${styles.card} ${styles[status]}`}
              onMouseEnter={() => setHoveredAgent(agent)}
              onMouseLeave={() => setHoveredAgent(null)}
            >
              <div className={styles.cardHeader}>
                <span className={styles.tag}>{agent.tag}</span>
                <span className={styles.accuracy}>{agent.accuracy} Acc</span>
              </div>
              <h3 className={styles.title}>{agent.name}</h3>
              <p className={styles.desc}>{agent.desc}</p>
              
              <div className={styles.metrics}>
                <div className={styles.metric}>
                  <span>Speed</span>
                  <strong>{agent.speed}</strong>
                </div>
                {status === "focused" && (
                  <div className={styles.connections}>
                    {agent.inputs[0] !== "Start" && (
                      <div className={styles.conn}>
                        <span className={styles.connLabel}>Inputs:</span>
                        <span className={styles.connVal}>{agent.inputs.join(", ")}</span>
                      </div>
                    )}
                    {agent.outputs[0] !== "Report" && (
                      <div className={styles.conn}>
                        <span className={styles.connLabel}>Outputs:</span>
                        <span className={styles.connVal}>{agent.outputs.join(", ")}</span>
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
