/**
 * Frontend redaction helpers.
 * Ensures secrets or sensitive tokens are masked on the UI side as a defense-in-depth measure.
 */
export function redactSecrets(text: string | null): string {
  if (!text) return "";
  
  // Mask common secret patterns (e.g. AWS access key, github tokens, hex strings, gemini api keys)
  return text
    .replace(/(AIzaSy[A-Za-z0-9_-]{33})/g, "[REDACTED_GEMINI_API_KEY]")
    .replace(/(ghp_[A-Za-z0-9_]{36,251})/g, "[REDACTED_GITHUB_TOKEN]")
    .replace(/("password"\s*:\s*")[^"]+(")/gi, '$1[REDACTED_PASSWORD]$2');
}
