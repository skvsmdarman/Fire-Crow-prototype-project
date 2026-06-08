"use client";

import React from "react";
import { ShieldCheck, Mail, GitPullRequest, CheckCircle2, AlertCircle } from "lucide-react";
import { Job } from "../types";

interface AuditVerificationCardProps {
  job: Job;
}

export default function AuditVerificationCard({ job }: AuditVerificationCardProps) {
  const isFinished = ["completed", "partial"].includes(job.status);
  const isRunning = ["queued", "running"].includes(job.status);

  // If the job is still running, we show a pending verification state
  if (isRunning) {
    return (
      <div style={{
        background: "rgba(30, 41, 59, 0.2)",
        border: "1px dashed rgba(255, 255, 255, 0.1)",
        borderRadius: "12px",
        padding: "20px",
        color: "#94a3b8",
        fontSize: "13px",
        display: "flex",
        alignItems: "center",
        gap: "14px",
        marginTop: "16px"
      }}>
        <ShieldCheck size={24} style={{ color: "#64748b", animation: "pulse 1.5s infinite" }} />
        <div>
          <strong style={{ display: "block", color: "#e2e8f0", fontSize: "14px", marginBottom: "2px" }}>
            Verification Pending
          </strong>
          Orchestrator pipeline is running. Deliverability verification will execute after phase completion.
        </div>
      </div>
    );
  }

  // If the job failed or was cancelled before completion phases, we show an uncompleted verification state
  if (!isFinished) {
    return (
      <div style={{
        background: "rgba(239, 68, 68, 0.05)",
        border: "1px solid rgba(239, 68, 68, 0.2)",
        borderRadius: "12px",
        padding: "20px",
        color: "#fca5a5",
        fontSize: "13px",
        display: "flex",
        alignItems: "flex-start",
        gap: "14px",
        marginTop: "16px"
      }}>
        <AlertCircle size={24} style={{ color: "#ef4444", flexShrink: 0, marginTop: "2px" }} />
        <div>
          <strong style={{ display: "block", color: "#fca5a5", fontSize: "14px", marginBottom: "4px" }}>
            Verification Incomplete
          </strong>
          The orchestrator process did not finish successfully. Deliverability phases (Email, GitHub MCP) were skipped due to job failure or cancellation.
        </div>
      </div>
    );
  }

  const emailDelivered = !!job.email_delivered;
  const githubIssuesRaised = !!job.github_issues_raised;
  const githubPrCreated = !!job.github_pr_created;

  return (
    <div style={{
      background: "linear-gradient(135deg, rgba(15, 23, 42, 0.6) 0%, rgba(30, 41, 59, 0.4) 100%)",
      backdropFilter: "blur(12px)",
      border: "1px solid rgba(255, 255, 255, 0.08)",
      borderRadius: "12px",
      padding: "20px",
      marginTop: "16px",
      position: "relative",
      overflow: "hidden",
      boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.3)"
    }}>
      {/* Decorative background glow */}
      <div style={{
        position: "absolute",
        top: "-20px",
        right: "-20px",
        width: "100px",
        height: "100px",
        borderRadius: "50%",
        background: emailDelivered && githubIssuesRaised ? "rgba(16, 185, 129, 0.1)" : "rgba(245, 158, 11, 0.1)",
        filter: "blur(40px)",
        pointerEvents: "none"
      }} />

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", borderBottom: "1px solid rgba(255, 255, 255, 0.05)", paddingBottom: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <ShieldCheck size={20} style={{ color: emailDelivered ? "#10b981" : "#f59e0b" }} />
          <div>
            <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#f8fafc", margin: 0 }}>
              POST-AUDIT VERIFICATION
            </h3>
            <span style={{ fontSize: "10px", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", fontFamily: "var(--font-mono), monospace" }}>
              Verified via Live Backend Ledger
            </span>
          </div>
        </div>

        <span style={{
          fontSize: "10px",
          color: emailDelivered && githubIssuesRaised ? "#10b981" : "#f59e0b",
          background: emailDelivered && githubIssuesRaised ? "rgba(16, 185, 129, 0.1)" : "rgba(245, 158, 11, 0.1)",
          border: emailDelivered && githubIssuesRaised ? "1px solid rgba(16, 185, 129, 0.2)" : "1px solid rgba(245, 158, 11, 0.2)",
          padding: "2px 8px",
          borderRadius: "4px",
          fontWeight: 600
        }}>
          {emailDelivered && githubIssuesRaised ? "VERIFIED SUCCESS" : "PARTIAL VERIFICATION"}
        </span>
      </div>

      {/* Verification Items */}
      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        {/* Email Verification */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: emailDelivered ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
            border: emailDelivered ? "1px solid rgba(16, 185, 129, 0.2)" : "1px solid rgba(239, 68, 68, 0.2)",
            flexShrink: 0
          }}>
            <Mail size={16} style={{ color: emailDelivered ? "#10b981" : "#ef4444" }} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2px" }}>
              <span style={{ fontSize: "13px", fontWeight: 500, color: "#e2e8f0" }}>Email Report Delivery</span>
              <span style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", color: emailDelivered ? "#10b981" : "#ef4444" }}>
                {emailDelivered ? (
                  <>
                    <CheckCircle2 size={12} />
                    <span>Delivered</span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={12} />
                    <span>Failed / Incomplete</span>
                  </>
                )}
              </span>
            </div>
            <p style={{ fontSize: "11px", color: "#94a3b8", margin: 0 }}>
              {emailDelivered 
                ? "The premium PDF report was generated and successfully transmitted via Resend API."
                : "The report generator and email delivery task failed to execute or did not complete."}
            </p>
          </div>
        </div>

        {/* GitHub Issues Verification */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: githubIssuesRaised ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
            border: githubIssuesRaised ? "1px solid rgba(16, 185, 129, 0.2)" : "1px solid rgba(239, 68, 68, 0.2)",
            flexShrink: 0
          }}>
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" style={{ color: githubIssuesRaised ? "#10b981" : "#ef4444" }}><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2px" }}>
              <span style={{ fontSize: "13px", fontWeight: 500, color: "#e2e8f0" }}>GitHub MCP Security Issues</span>
              <span style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", color: githubIssuesRaised ? "#10b981" : "#ef4444" }}>
                {githubIssuesRaised ? (
                  <>
                    <CheckCircle2 size={12} />
                    <span>Issues Raised</span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={12} />
                    <span>Not Raised / Skipped</span>
                  </>
                )}
              </span>
            </div>
            <p style={{ fontSize: "11px", color: "#94a3b8", margin: 0 }}>
              {githubIssuesRaised 
                ? "Security findings were successfully parsed and raised as tracking issues on GitHub."
                : "No tracking issues were raised on GitHub (either skipped, failed, or no vulnerabilities found)."}
            </p>
          </div>
        </div>

        {/* GitHub PR Verification */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: githubPrCreated ? "rgba(16, 185, 129, 0.1)" : "rgba(255, 255, 255, 0.05)",
            border: githubPrCreated ? "1px solid rgba(16, 185, 129, 0.2)" : "1px solid rgba(255, 255, 255, 0.1)",
            flexShrink: 0
          }}>
            <GitPullRequest size={16} style={{ color: githubPrCreated ? "#10b981" : "#64748b" }} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "2px" }}>
              <span style={{ fontSize: "13px", fontWeight: 500, color: "#e2e8f0" }}>Automated Remediation PR</span>
              <span style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", color: githubPrCreated ? "#10b981" : "#64748b" }}>
                {githubPrCreated ? (
                  <>
                    <CheckCircle2 size={12} />
                    <span>PR Created</span>
                  </>
                ) : (
                  <span>No PR Created</span>
                )}
              </span>
            </div>
            <p style={{ fontSize: "11px", color: "#94a3b8", margin: 0 }}>
              {githubPrCreated 
                ? "An automated patching pull request was generated and successfully submitted."
                : "No code changes were automatically proposed/submitted as a PR for this scan."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
