"use client";

import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import Card from "../../../components/ui/Card";
import styles from "../../../app/dashboard/page.module.css";
import { LogLine } from "../../../shared/hooks/useSSE";
import { Search, Copy, Download, Check, ArrowDown } from "lucide-react";

interface LogStreamProps {
  logs: LogLine[];
  streamActive: boolean;
  hasSelection: boolean;
}

function formatLogDateTime(value: string | null): string {
  if (!value) return "Pending";
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(new Date(value));
  } catch {
    return value;
  }
}

const getAgentBadgeStyle = (agentName: string) => {
  const name = (agentName || "").toUpperCase();
  if (name.includes("GITHUB_MCP") || name.includes("GITHUB")) {
    return { backgroundColor: "rgba(56, 189, 248, 0.1)", color: "#38bdf8", borderColor: "rgba(56, 189, 248, 0.2)" };
  }
  if (name.includes("REPORTER")) {
    return { backgroundColor: "rgba(244, 63, 94, 0.1)", color: "#f43f5e", borderColor: "rgba(244, 63, 94, 0.2)" };
  }
  if (name.includes("SAST") || name.includes("GOOGLE_AGENT")) {
    return { backgroundColor: "rgba(16, 185, 129, 0.1)", color: "#10b981", borderColor: "rgba(16, 185, 129, 0.2)" };
  }
  if (name.includes("SYSTEM") || name.includes("ORCHESTRATOR")) {
    return { backgroundColor: "rgba(239, 68, 68, 0.1)", color: "#ef4444", borderColor: "rgba(239, 68, 68, 0.2)" };
  }
  return { backgroundColor: "rgba(255, 255, 255, 0.05)", color: "#a3a3a3", borderColor: "rgba(255, 255, 255, 0.1)" };
};

export default function LogStream({ logs, streamActive, hasSelection }: LogStreamProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (autoScroll && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleCopy = useCallback(() => {
    if (logs.length === 0) return;
    const text = logs
      .map(
        (log) =>
          `[${formatLogDateTime(log.timestamp)}] [${log.agent_name}] [${log.log_level}] ${log.message}`
      )
      .join("\n");
    void navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [logs]);

  const handleDownload = useCallback(() => {
    if (logs.length === 0) return;
    const text = logs
      .map(
        (log) =>
          `[${formatLogDateTime(log.timestamp)}] [${log.agent_name}] [${log.log_level}] ${log.message}`
      )
      .join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit_logs_${Date.now()}.log`;
    a.click();
    URL.revokeObjectURL(url);
  }, [logs]);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        (log.message || "").toLowerCase().includes(q) ||
        (log.agent_name || "").toLowerCase().includes(q) ||
        (log.log_level || "").toLowerCase().includes(q)
      );
    });
  }, [logs, searchQuery]);

  return (
    <Card variant="surface" className={styles.panel} style={{ display: "flex", flexDirection: "column", padding: 0, overflow: "hidden", border: "1px solid #222", background: "#0b0c10" }}>
      {/* MacOS Terminal Window Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "8px",
        padding: "10px 16px",
        background: "#12141c",
        borderBottom: "1px solid #1f2230",
        userSelect: "none"
      }}>
        {/* MacOS Window Dots */}
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <div style={{ width: "12px", height: "12px", borderRadius: "50%", background: "#ff5f56" }} />
          <div style={{ width: "12px", height: "12px", borderRadius: "50%", background: "#ffbd2e" }} />
          <div style={{ width: "12px", height: "12px", borderRadius: "50%", background: "#27c93f" }} />
          <span style={{ marginLeft: "12px", fontSize: "11px", fontFamily: "var(--font-mono), monospace", color: "#6b7280", letterSpacing: "0.05em" }}>
            bash - firecrow-orchestrator
          </span>
        </div>

        {/* Live/Saved badge */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", width: "100%" }}>
          <span style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
            fontSize: "10px",
            fontFamily: "var(--font-mono), monospace",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: streamActive ? "#10b981" : "#6b7280",
            background: streamActive ? "rgba(16, 185, 129, 0.1)" : "rgba(107, 114, 128, 0.1)",
            padding: "2px 8px",
            borderRadius: "4px",
            border: streamActive ? "1px solid rgba(16, 185, 129, 0.2)" : "1px solid rgba(107, 114, 128, 0.2)"
          }}>
            {streamActive && (
              <span style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "#10b981",
                boxShadow: "0 0 8px #10b981",
                animation: "pulse 1.5s infinite"
              }} />
            )}
            {streamActive ? "LIVE" : "ARCHIVED"}
          </span>
        </div>
      </div>

      {/* Terminal Toolbar (Search, Filter, Copy, Download, Auto-Scroll) */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "8px",
        padding: "10px 16px",
        background: "#0c0e15",
        borderBottom: "1px solid #1b1d28"
      }}>
        {/* Search / Filter input */}
        <div style={{ position: "relative", width: "100%", flexBasis: "100%" }}>
          <Search size={14} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "#6b7280" }} />
          <input
            type="text"
            placeholder="Search terminal logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 12px 6px 32px",
              fontSize: "12px",
              fontFamily: "var(--font-mono), monospace",
              color: "#e2e8f0",
              background: "#161925",
              border: "1px solid #2d3142",
              borderRadius: "6px",
              outline: "none",
              transition: "border-color 0.2s",
            }}
            onFocus={(e) => e.target.style.borderColor = "#3b82f6"}
            onBlur={(e) => e.target.style.borderColor = "#2d3142"}
          />
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", width: "100%" }}>
          {/* Auto-Scroll Toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            title="Toggle Autoscroll to bottom"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              fontSize: "11px",
              fontFamily: "var(--font-mono), monospace",
              color: autoScroll ? "#38bdf8" : "#94a3b8",
              background: autoScroll ? "rgba(56, 189, 248, 0.08)" : "#161925",
              border: autoScroll ? "1px solid rgba(56, 189, 248, 0.3)" : "1px solid #2d3142",
              borderRadius: "6px",
              cursor: "pointer",
              transition: "all 0.15s"
            }}
          >
            <ArrowDown size={12} style={{ transform: autoScroll ? "none" : "rotate(-90deg)", transition: "transform 0.15s" }} />
            <span>Scroll {autoScroll ? "ON" : "OFF"}</span>
          </button>

          {/* Copy Logs */}
          <button
            onClick={handleCopy}
            disabled={logs.length === 0}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              fontSize: "11px",
              fontFamily: "var(--font-mono), monospace",
              color: logs.length === 0 ? "#475569" : "#e2e8f0",
              background: "#161925",
              border: "1px solid #2d3142",
              borderRadius: "6px",
              cursor: logs.length === 0 ? "not-allowed" : "pointer",
              transition: "all 0.15s"
            }}
          >
            {copied ? <Check size={12} style={{ color: "#10b981" }} /> : <Copy size={12} />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>

          {/* Download Logs */}
          <button
            onClick={handleDownload}
            disabled={logs.length === 0}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              fontSize: "11px",
              fontFamily: "var(--font-mono), monospace",
              color: logs.length === 0 ? "#475569" : "#e2e8f0",
              background: "#161925",
              border: "1px solid #2d3142",
              borderRadius: "6px",
              cursor: logs.length === 0 ? "not-allowed" : "pointer",
              transition: "all 0.15s"
            }}
          >
            <Download size={12} />
            <span>Save</span>
          </button>
        </div>
      </div>

      {/* Log Console Output Area */}
      <div
        ref={listRef}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          height: "360px",
          overflowY: "auto",
          fontFamily: "var(--font-mono), monospace",
          fontSize: "12px",
          background: "#08090d",
          padding: "16px",
          color: "#e2e8f0"
        }}
      >
        {filteredLogs.length === 0 ? (
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            color: "#475569",
            fontSize: "13px",
            textAlign: "center",
            fontStyle: "italic"
          }}>
            {hasSelection
              ? searchQuery
                ? "No logs matched your search filter."
                : "No orchestrator logs generated yet. Starting execution..."
              : "Select an audit job to view live output console."}
          </div>
        ) : (
          filteredLogs.map((log, index) => {
            const badgeStyle = getAgentBadgeStyle(log.agent_name);
            const rawIndex = logs.indexOf(log);
            const lineNum = String(rawIndex + 1).padStart(3, "0");

            return (
              <div
                key={`${log.id}-${log.timestamp}-${index}`}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "12px",
                  lineHeight: "1.5",
                  padding: "2px 0",
                  borderBottom: "1px solid rgba(255, 255, 255, 0.01)"
                }}
              >
                {/* Line Number */}
                <span style={{ color: "#334155", userSelect: "none", flexShrink: 0, width: "24px", textAlign: "right" }}>
                  {lineNum}
                </span>

                {/* Timestamp */}
                <span style={{ color: "#475569", flexShrink: 0, userSelect: "none" }}>
                  [{formatLogDateTime(log.timestamp)}]
                </span>

                {/* Agent Badge */}
                <span style={{
                  display: "inline-block",
                  padding: "1px 6px",
                  borderRadius: "3px",
                  fontSize: "9px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  border: "1px solid transparent",
                  flexShrink: 0,
                  minWidth: "90px",
                  textAlign: "center",
                  ...badgeStyle
                }}>
                  {log.agent_name}
                </span>

                {/* Log Divider */}
                <span style={{ color: "#1e293b", userSelect: "none" }}>|</span>

                {/* Log Message */}
                <p style={{
                  margin: 0,
                  color: log.log_level === "ERROR" ? "#f43f5e" : log.log_level === "WARNING" ? "#fbbf24" : "#cbd5e1",
                  wordBreak: "break-all",
                  whiteSpace: "pre-wrap",
                  flex: 1
                }}>
                  {log.message}
                </p>
              </div>
            );
          })
        )}
      </div>

      <style jsx global>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.9); }
        }
      `}</style>
    </Card>
  );
}
