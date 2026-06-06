"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import Card from "../../../components/ui/Card";
import Badge from "../../../components/ui/Badge";
import styles from "../page.module.css";

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

export default function FindingsList({ findings, loading }: FindingsListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <Card variant="surface" className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>Findings</div>
          <h2>{loading ? "Loading" : `${findings.length} total`}</h2>
        </div>
      </div>

      <div className={styles.findingList}>
        {findings.length === 0 ? (
          <div className={styles.emptyState}>
            {loading ? "Checking findings records..." : "No findings released for this audit."}
          </div>
        ) : (
          findings.map((finding) => {
            const isExpanded = expandedId === finding.id;
            return (
              <div
                key={finding.id}
                className={[
                  styles.findingRowContainer,
                  isExpanded ? styles.findingExpanded : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <button
                  type="button"
                  onClick={() => toggleExpand(finding.id)}
                  className={styles.findingRowHeader}
                >
                  <div className={styles.findingRowMain}>
                    <Badge variant="severity" type={finding.severity}>
                      {finding.severity}
                    </Badge>
                    <h3 className={styles.findingTitle}>{finding.title}</h3>
                  </div>
                  <div className={styles.findingRowMeta}>
                    <span className={styles.findingAgent}>{finding.agent_source}</span>
                    <strong className={styles.findingCvss}>
                      {finding.cvss_score ? `CVSS ${finding.cvss_score.toFixed(1)}` : "CVSS -"}
                    </strong>
                    <ChevronDown
                      size={16}
                      className={[
                        styles.expandArrow,
                        isExpanded ? styles.arrowRotated : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    />
                  </div>
                </button>

                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ type: "spring", stiffness: 300, damping: 26 }}
                      className={styles.findingDetailPanel}
                    >
                      <div className={styles.findingDetailContent}>
                        <p className={styles.findingDescription}>{finding.description}</p>
                        
                        {finding.cvss_vector && (
                          <div className={styles.detailSection}>
                            <h4>CVSS Vector</h4>
                            <code className={styles.vectorCode}>{finding.cvss_vector}</code>
                          </div>
                        )}

                        {finding.evidence && (
                          <div className={styles.detailSection}>
                            <h4>Evidence</h4>
                            <pre className={styles.evidenceBlock}>
                              <code>{finding.evidence}</code>
                            </pre>
                          </div>
                        )}

                        {finding.remediation && (
                          <div className={styles.detailSection}>
                            <h4>Remediation Plan</h4>
                            <div className={styles.remediationContent}>
                              {finding.remediation}
                            </div>
                          </div>
                        )}
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
