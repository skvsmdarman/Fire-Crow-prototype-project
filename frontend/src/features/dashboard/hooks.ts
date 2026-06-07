import { useMemo } from "react";
import { Job, Finding, Severity } from "../audits/types";
import { DashboardMetrics } from "./types";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled", "partial"];

export function calculateRiskScore(findings: Finding[]): number | null {
  if (findings.length === 0) return null;
  const weights: Record<Severity, number> = { critical: 28, high: 18, medium: 9, low: 4, info: 0 };
  return Math.min(100, findings.reduce((score, finding) => score + weights[finding.severity], 0));
}

export function postureLabel(score: number | null, activeJobs: number): string {
  if (activeJobs > 0) return "Audit running";
  if (score === null) return "Awaiting first audit";
  if (score >= 80) return "Critical attention";
  if (score >= 55) return "High risk";
  if (score >= 25) return "Needs review";
  return "Controlled";
}

export function useDashboardMetrics(jobs: Job[], findings: Finding[]): DashboardMetrics {
  return useMemo(() => {
    const totalJobs = jobs.length;
    const activeJobs = jobs.filter((j) => !TERMINAL_STATUSES.includes(j.status)).length;

    let criticalFindings = 0;
    let highFindings = 0;
    let mediumFindings = 0;
    let lowFindings = 0;

    findings.forEach((finding) => {
      switch (finding.severity) {
        case "critical":
          criticalFindings++;
          break;
        case "high":
          highFindings++;
          break;
        case "medium":
          mediumFindings++;
          break;
        case "low":
          lowFindings++;
          break;
      }
    });

    const riskScore = calculateRiskScore(findings);
    const posture = postureLabel(riskScore, activeJobs);

    return {
      totalJobs,
      activeJobs,
      criticalFindings,
      highFindings,
      mediumFindings,
      lowFindings,
      posture,
      riskScore,
    };
  }, [jobs, findings]);
}
