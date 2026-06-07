"use client";

import React, { useEffect, useState, useRef } from "react";
import { AlertTriangle, FileText, Terminal } from "lucide-react";
import Card from "../../../components/ui/Card";
import styles from "../page.module.css";

interface MetricsRowProps {
  activeAudits: number;
  totalJobs: number;
  criticalFindings: number;
  latestReport: string | null;
}

function AnimatedNumber({ value }: { value: number }) {
  const [displayValue, setDisplayValue] = useState(value);
  const prevValueRef = useRef(value);

  useEffect(() => {
    let active = true;
    const start = prevValueRef.current;
    const end = value;
    prevValueRef.current = value;

    if (start === end) {
      return;
    }
    const duration = 800; // ms
    const increment = (end - start) / (duration / 16);
    let current = start;
    const timer = setInterval(() => {
      current += increment;
      if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
        clearInterval(timer);
        if (active) setDisplayValue(end);
      } else {
        if (active) setDisplayValue(Math.floor(current));
      }
    }, 16);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [value]);

  return <>{displayValue}</>;
}

export default function MetricsRow({
  activeAudits,
  totalJobs,
  criticalFindings,
  latestReport,
}: MetricsRowProps) {
  return (
    <section className={styles.metricsGrid} aria-label="Audit metrics">
      <Card interactive hoverLift variant="surface" className={styles.metricCard}>
        <div className={styles.metricHeader}>
          <span>Active</span>
          <span className={styles.metricAccent} aria-hidden="true" />
        </div>
        <strong className={styles.metricValue}><AnimatedNumber value={activeAudits} /></strong>
        <p className={styles.metricNote}>{activeAudits === 1 ? "1 audit running" : `${activeAudits} audits running`}</p>
      </Card>

      <Card interactive hoverLift variant="surface" className={styles.metricCard}>
        <div className={styles.metricHeader}>
          <span>Jobs</span>
          <Terminal size={16} className={styles.metricIcon} />
        </div>
        <strong className={styles.metricValue}><AnimatedNumber value={totalJobs} /></strong>
        <p className={styles.metricNote}>Saved in this workspace</p>
      </Card>

      <Card
        interactive
        hoverLift
        variant="surface"
        className={[
          styles.metricCard,
          criticalFindings > 0 ? styles.metricDanger : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <div className={styles.metricHeader}>
          <span>Critical</span>
          <AlertTriangle size={16} className={styles.metricIcon} />
        </div>
        <strong className={styles.metricValue}><AnimatedNumber value={criticalFindings} /></strong>
        <p className={styles.metricNote}>Need immediate review</p>
      </Card>

      <Card interactive hoverLift variant="surface" className={styles.metricCard}>
        <div className={styles.metricHeader}>
          <span>Report</span>
          <FileText size={16} className={styles.metricIcon} />
        </div>
        <strong className={styles.metricValue} style={{ fontSize: latestReport ? "20px" : "28px" }}>
          {latestReport ? "Ready" : "None"}
        </strong>
        <p className={styles.metricNote}>{latestReport ? "Latest export available" : "No export yet"}</p>
      </Card>
    </section>
  );
}
