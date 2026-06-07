"use client";

import React, { useEffect, useRef } from "react";
import Card from "../../../components/ui/Card";
import styles from "../page.module.css";

interface LogLine {
  id: number;
  agent_name: string;
  log_level: string;
  message: string;
  timestamp: string;
}

interface LogStreamProps {
  logs: LogLine[];
  streamActive: boolean;
  hasSelection: boolean;
}

function formatDateTime(value: string | null): string {
  if (!value) return "Pending";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

export default function LogStream({ logs, streamActive, hasSelection }: LogStreamProps) {
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <Card variant="surface" className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <div className={styles.sectionKicker}>Audit log</div>
          <h2>Execution history</h2>
        </div>
        <div className={styles.streamStatusBlock}>
          <span
            className={[
              styles.streamState,
              streamActive ? styles.streamLive : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {streamActive && <span className={styles.streamDot} />}
            {streamActive ? "live" : "saved"}
          </span>
        </div>
      </div>

      <div ref={listRef} className={styles.logList}>
        {logs.length === 0 ? (
          <div className={styles.emptyState}>
            {hasSelection ? "No saved logs are available for this audit yet." : "Select an audit to view its logs."}
          </div>
        ) : (
          logs.map((log, index) => {
            const levelClass = styles[log.log_level.toLowerCase()] || "";
            return (
              <div key={`${log.id}-${log.timestamp}-${index}`} className={styles.logRow}>
                <span className={styles.logTime}>{formatDateTime(log.timestamp)}</span>
                <span className={[styles.logAgent, levelClass].filter(Boolean).join(" ")}>
                  {log.agent_name}
                </span>
                <span className={styles.logDivider}>|</span>
                <p className={styles.logMessage}>{log.message}</p>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
