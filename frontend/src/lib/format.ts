import { Severity } from "./types";

export function formatRelativeDate(value: string | null | undefined): string {
  if (!value) {
    return "Pending";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function severityRank(severity: Severity): number {
  switch (severity) {
    case "critical":
      return 5;
    case "high":
      return 4;
    case "medium":
      return 3;
    case "low":
      return 2;
    default:
      return 1;
  }
}

export function formatRepoName(repoUrl: string): string {
  try {
    const url = new URL(repoUrl);
    return url.pathname.replace(/^\/+/, "");
  } catch {
    return repoUrl;
  }
}

export function scoreLabel(score: number | null | undefined): string {
  if (score == null) {
    return "Not scored";
  }
  if (score >= 9) {
    return "Critical posture";
  }
  if (score >= 7) {
    return "High exposure";
  }
  if (score >= 4) {
    return "Moderate exposure";
  }
  return "Contained exposure";
}
