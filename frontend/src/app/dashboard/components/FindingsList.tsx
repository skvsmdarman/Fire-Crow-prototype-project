"use client";

import React, { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import Card from "../../../components/ui/Card";
import Badge from "../../../components/ui/Badge";
import styles from "../page.module.css";
import mobile from "../mobile.module.css";

interface Finding {
  id: string;
  agent_source: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  cvss_score: number | null;
  cvss_vector: string | null;
  evidence: string | null;
  remediation: string | null;
}

interface FindingsListProps {
  findings: Finding[];
  loading: boolean;
}

type FindingFilter = "all" | Finding["severity"];

const FILTERS: { id: FindingFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "critical", label: "Critical" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
  { id: "info", label: "Passed/Resolved" },
];

function severityLabel(severity: Finding["severity"]): string {
  return severity === "info" ? "Passed/Resolved" : severity;
}

export default function FindingsList({ findings, loading }: FindingsListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<FindingFilter>("all");

  const filteredFindings = useMemo(
    () => (filter === "all" ? findings : findings.filter((finding) => finding.severity === filter)),
    [filter, findings],
  );

  const counts = useMemo(() => {
    return findings.reduce<Record<FindingFilter, number>>(
      (acc, finding) => {
        acc.all += 1;
        acc[finding.severity] += 1;
        return acc;
      },
      { all: 0, critical: 0, high: 0, medium: 0, low: 0, info: 0 },
    );
  }, [findings]);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <Card variant="surface" className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>Findings</div>
          <h2>{loading ? "Loading" : `${filteredFindings.length} shown`}</h2>
        </div>
      </div>

      <div className={mobile.filterRail} role="toolbar" aria-label="Filter findings by severity">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={filter === item.id ? mobile.filterChipActive : mobile.filterChip}
            aria-pressed={filter === item.id}
            onClick={() => setFilter(item.id)}
          >
            <span>{item.label}</span>
            <strong>{counts[item.id]}</strong>
          </button>
        ))}
      </div>

      <div className={styles.findingList}>
        {findings.length === 0 ? (
          <div className={styles.emptyState}>{loading ? "Checking findings records..." : "No findings released for this audit."}</div>
        ) : filteredFindings.length === 0 ? (
          <div className={styles.emptyState}>No findings match this severity filter.</div>
        ) : (
          filteredFindings.map((finding) => {
            const isExpanded = expandedId === finding.id;
            return (
              <div key={finding.id} className={[styles.findingRowContainer, isExpanded ? styles.findingExpanded : ""].filter(Boolean).join(" ")}>
                <button type="button" onClick={() => toggleExpand(finding.id)} className={styles.findingRowHeader} aria-expanded={isExpanded}>
                  <div className={styles.findingRowMain}>
                    <Badge variant="severity" type={finding.severity}>{severityLabel(finding.severity)}</Badge>
                    <h3 className={styles.findingTitle}>{finding.title}</h3>
                  </div>
                  <div className={styles.findingRowMeta}>
                    <span className={styles.findingAgent}>{finding.agent_source}</span>
                    <strong className={styles.findingCvss}>{finding.cvss_score ? `CVSS ${finding.cvss_score.toFixed(1)}` : "CVSS not set"}</strong>
                    <ChevronDown size={16} aria-hidden="true" className={[styles.expandArrow, isExpanded ? styles.arrowRotated : ""].filter(Boolean).join(" ")} />
                  </div>
                </button>

                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 300, damping: 26 }} className={styles.findingDetailPanel}>
                      <div className={styles.findingDetailContent}>
                        <section className={styles.detailSection}>
                          <h4>Risk explanation</h4>
                          <p className={styles.findingDescription}>{finding.description}</p>
                        </section>

                        {finding.cvss_vector && (
                          <div className={styles.detailSection}>
                            <h4>CVSS Vector</h4>
                            <code className={styles.vectorCode}>{finding.cvss_vector}</code>
                          </div>
                        )}

                        {finding.evidence && (
                          <div className={styles.detailSection}>
                            <h4>Evidence</h4>
                            <pre className={styles.evidenceBlock}><code>{finding.evidence}</code></pre>
                          </div>
                        )}

                        {finding.remediation && (
                          <div className={styles.detailSection}>
                            <h4>Recommended fix</h4>
                            <div className={styles.remediationContent}>{finding.remediation}</div>
                          </div>
                        )}

                        <div className={styles.detailSection}>
                          <h4>Verification steps</h4>
                          <p className={styles.findingDescription}>Re-run an authorized audit after applying the remediation and confirm this finding is absent or resolved in the next report.</p>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
