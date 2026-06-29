"use client";

import Link from "next/link";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { request } from "../../lib/request";
import { formatRepoName, severityRank } from "../../lib/format";
import { Job, JobDetailResponse } from "../../lib/types";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { SiteHeader } from "../SiteChrome";

export function FindingsConsole() {
  const searchParams = useSearchParams();
  const requestedJobId = searchParams.get("jobId") ?? searchParams.get("job_id");

  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(requestedJobId);
  const [jobDetail, setJobDetail] = useState<JobDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const deferredSearch = useDeferredValue(search.trim().toLowerCase());

  useEffect(() => {
    let cancelled = false;
    request<Job[]>("/audit/jobs")
      .then((nextJobs) => {
        if (!cancelled) {
          setJobs(nextJobs);
          if (!selectedJobId && nextJobs.length > 0) {
            setSelectedJobId(nextJobs[0].id);
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load audit jobs list.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedJobId]);

  useEffect(() => {
    if (!selectedJobId) return;
    let cancelled = false;

    request<JobDetailResponse>(`/audit/job/${selectedJobId}`)
      .then((detail) => {
        if (!cancelled) {
          setJobDetail(detail);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load findings detail for this job.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedJobId]);

  const findings = useMemo(() => {
    const source = jobDetail?.findings ?? [];
    return [...source]
      .filter((finding) => {
        if (!deferredSearch) return true;
        return [finding.title, finding.description, finding.agent_source, finding.severity]
          .join(" ")
          .toLowerCase()
          .includes(deferredSearch);
      })
      .sort((left, right) => severityRank(right.severity) - severityRank(left.severity));
  }, [deferredSearch, jobDetail?.findings]);

  const selectedJob = jobs.find((j) => j.id === selectedJobId) ?? null;

  return (
    <div className="fc-page">
      <SiteHeader ctaHref="/dashboard" ctaLabel="Back to Dashboard" />
      <main className="fc-shell fc-dashboard-shell">
        <div className="fc-dashboard-grid">
          <Card className="fc-sidebar">
            <div>
              <div className="fc-kicker">Navigation</div>
              <h2 className="fc-panel-title" style={{ marginTop: 10 }}>Findings Review</h2>
              <div className="fc-copy" style={{ marginTop: 10 }}>
                Analyze identified vulnerabilities and security posture across your audited repositories.
              </div>
            </div>
            <div className="fc-sidebar-nav">
              <Link className="fc-sidebar-tab" href="/dashboard">Dashboard</Link>
              <Link className="fc-sidebar-tab" href="/dashboard/findings" data-active="true">Findings</Link>
              <Link className="fc-sidebar-tab" href="/dashboard/signals">Signals & AI</Link>
              <Link className="fc-sidebar-tab" href="/dashboard/settings">Settings</Link>
            </div>
          </Card>

          <div className="fc-dashboard-main">
            {error && <div className="fc-form-error">{error}</div>}

            <Card className="fc-panel">
              <div className="fc-panel-head" style={{ gap: 20, flexWrap: "wrap" }}>
                <div>
                  <div className="fc-kicker">Select Audit Run</div>
                  {selectedJob ? (
                    <h2 className="fc-panel-title">{formatRepoName(selectedJob.repo_url)} ({selectedJob.repo_branch})</h2>
                  ) : (
                    <h2 className="fc-panel-title">No Audit Selected</h2>
                  )}
                </div>

                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <select
                    className="fc-input"
                    value={selectedJobId ?? ""}
                    onChange={(e) => startTransition(() => setSelectedJobId(e.target.value || null))}
                    style={{ background: "var(--fc-bg-secondary)", color: "inherit", padding: "8px 12px", border: "1px solid var(--fc-border)" }}
                    aria-label="Select audit run to filter findings"
                  >
                    {jobs.map((job) => (
                      <option key={job.id} value={job.id}>
                        {formatRepoName(job.repo_url)} ({job.repo_branch})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </Card>

            <Card className="fc-panel">
              <div className="fc-panel-head">
                <div>
                  <div className="fc-kicker">Vulnerabilities</div>
                  <h3 className="fc-panel-title">Vulnerability findings ({findings.length})</h3>
                </div>
                <div style={{ minWidth: 260 }}>
                  <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search findings, categories..."
                  />
                </div>
              </div>

              {loading ? (
                <div className="fc-copy">Loading findings details...</div>
              ) : findings.length ? (
                <div className="fc-findings">
                  {findings.map((finding) => (
                    <div className="fc-finding" key={finding.id}>
                      <div className="fc-finding-head">
                        <strong>{finding.title}</strong>
                        <Badge
                          tone={
                            finding.severity === "critical"
                              ? "critical"
                              : finding.severity === "high"
                                ? "warning"
                                : finding.severity === "medium"
                                  ? "info"
                                  : "neutral"
                          }
                        >
                          {finding.severity}
                        </Badge>
                      </div>
                      <div className="fc-copy" style={{ marginTop: 10 }}>
                        {finding.description}
                      </div>
                      <div className="fc-mini-list" style={{ marginTop: 12 }}>
                        <div className="fc-muted">Agent Source: {finding.agent_source}</div>
                        {finding.cvss_score != null && (
                          <div className="fc-muted">CVSS Score: {finding.cvss_score}</div>
                        )}
                        {finding.evidence && (
                          <div className="fc-copy" style={{ marginTop: 6 }}>
                            <strong>Evidence:</strong> <span className="fc-monospace">{finding.evidence}</span>
                          </div>
                        )}
                        {finding.remediation && (
                          <div className="fc-copy" style={{ marginTop: 6 }}>
                            <strong>Remediation:</strong> {finding.remediation}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="fc-empty">No findings match your criteria.</div>
              )}
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
