export function sanitizeRepoUrl(repoUrl: string): string {
  return repoUrl.replace(/\/\/([^/@\s]+)@/, "//***@");
}

export function shortRepoName(repoUrl: string): string {
  return sanitizeRepoUrl(repoUrl)
    .replace(/^https:\/\/github\.com\//, "")
    .replace(/\/$/, "");
}

export function formatDateTime(value: string | null): string {
  if (!value) return "Pending";
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}
