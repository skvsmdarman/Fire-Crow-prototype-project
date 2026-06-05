"use client";

import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled" | "partial";
type Severity = "critical" | "high" | "medium" | "low" | "info";
type Section = "operations" | "reports" | "agents" | "settings";

interface Job {
  id: string;
  user_id: string;
  repo_url: string;
  repo_branch: string;
  status: JobStatus;
  created_at: string;
  finished_at: string | null;
  cancel_requested: boolean;
  cancel_requested_at: string | null;
  report_pdf_url: string | null;
  error_message: string | null;
}

interface Finding {
  id: string;
  agent_source: string;
  title: string;
  description: string;
  severity: Severity;
  cvss_score: number | null;
  cvss_vector: string | null;
  evidence: string | null;
  remediation: string | null;
}

interface JobDetail {
  job: Job;
  findings: Finding[];
}

interface LogLine {
  id: number;
  agent_name: string;
  log_level: string;
  message: string;
  timestamp: string;
}

interface SystemAgent {
  name: string;
  role: string;
  status: string;
}

interface SystemStatus {
  api: string;
  database: string;
  debug: boolean;
  sandbox_mode: "simulation" | "docker";
  stats: {
    jobs: number;
    findings: number;
  };
  integrations: Record<string, boolean>;
  agents: SystemAgent[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const PIPELINE = [
  "INTAKE",
  "STATIC SCAN",
  "SANDBOX",
  "NETWORK",
  "ATTACK",
  "EXPLOIT",
  "SCORING",
  "REPORTER",
  "GOOGLE AGENT",
  "CLEANUP",
];

const TERMINAL_STATUSES: JobStatus[] = ["completed", "failed", "cancelled", "partial"];

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function shortRepoName(repoUrl: string): string {
  return repoUrl.replace(/^https:\/\/github\.com\//, "").replace(/\/$/, "");
}

function formatDateTime(value: string | null): string {
  if (!value) return "Pending";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusLabel(job: Job): string {
  if (job.cancel_requested && !TERMINAL_STATUSES.includes(job.status)) {
    return "cancelling";
  }
  return job.status;
}

function pipelineIndex(status: JobStatus, logs: LogLine[]): number {
  if (status === "queued") return 0;
  if (status === "completed" || status === "partial") return PIPELINE.length - 1;
  if (status === "failed" || status === "cancelled") return -1;

  let index = 1;
  for (const log of logs) {
    const message = log.message.toLowerCase();
    if (message.includes("static") || message.includes("sast")) index = Math.max(index, 1);
    if (message.includes("sandbox") || message.includes("kali")) index = Math.max(index, 2);
    if (message.includes("port") || message.includes("nmap") || message.includes("network")) index = Math.max(index, 3);
    if (message.includes("attack") || message.includes("sqlmap") || message.includes("nuclei")) index = Math.max(index, 4);
    if (message.includes("exploit") || message.includes("proof")) index = Math.max(index, 5);
    if (message.includes("cvss") || message.includes("scoring")) index = Math.max(index, 6);
    if (message.includes("report") || message.includes("pdf")) index = Math.max(index, 7);
    if (message.includes("google") || message.includes("gmail") || message.includes("pr risk")) index = Math.max(index, 8);
    if (message.includes("cleanup") || message.includes("deprovision")) index = Math.max(index, 9);
  }
  return index;
}

export default function Dashboard() {
  const router = useRouter();
  const [activeSection, setActiveSection] = useState<Section>("operations");
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [userId, setUserId] = useState("");
  const [authReady, setAuthReady] = useState(false);

  const [repoUrl, setRepoUrl] = useState("");
  const [repoBranch, setRepoBranch] = useState("main");
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJobDetail, setSelectedJobDetail] = useState<JobDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const [logs, setLogs] = useState<LogLine[]>([]);
  const [streamActive, setStreamActive] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [systemError, setSystemError] = useState("");
  const [loadingSystem, setLoadingSystem] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const terminalEndRef = useRef<HTMLDivElement | null>(null);

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) || selectedJobDetail?.job || null,
    [jobs, selectedJobDetail, selectedJobId],
  );

  const findings = selectedJobDetail?.findings || [];
  const activeJobs = jobs.filter((job) => job.status === "queued" || job.status === "running").length;
  const criticalFindings = findings.filter((finding) => finding.severity === "critical").length;
  const latestReport = jobs.find((job) => job.report_pdf_url)?.report_pdf_url || null;
  const reportJobs = jobs.filter((job) => TERMINAL_STATUSES.includes(job.status));

  const fetchSystemStatus = useCallback(async () => {
    setLoadingSystem(true);
    setSystemError("");
    try {
      const response = await fetch(`${API_BASE_URL}/system/status`);
      if (!response.ok) {
        throw new Error("System status endpoint is unavailable.");
      }
      setSystemStatus((await response.json()) as SystemStatus);
    } catch (error: unknown) {
      setSystemError(getErrorMessage(error, "System status endpoint is unavailable."));
    } finally {
      setLoadingSystem(false);
    }
  }, []);

  const fetchJobs = useCallback(async () => {
    if (!token) return;
    setLoadingJobs(true);
    try {
      const response = await fetch(`${API_BASE_URL}/audit/jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = (await response.json()) as Job[];
        setJobs(data);
        setSelectedJobId((current) => current || data[0]?.id || null);
      }
    } finally {
      setLoadingJobs(false);
    }
  }, [token]);

  const fetchJobDetail = useCallback(
    async (jobId: string) => {
      if (!token) return;
      setLoadingDetail(true);
      try {
        const response = await fetch(`${API_BASE_URL}/audit/job/${jobId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          setSelectedJobDetail((await response.json()) as JobDetail);
        }
      } finally {
        setLoadingDetail(false);
      }
    },
    [token],
  );

  const stopLogStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStreamActive(false);
  }, []);

  const startLogStream = useCallback(
    async (jobId: string) => {
      if (!token) return;
      stopLogStream();
      setLogs([]);
      setStreamActive(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const response = await fetch(`${API_BASE_URL}/audit/${jobId}/stream`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });

        if (!response.body) {
          throw new Error("Log stream unavailable.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const rawLine of lines) {
            if (!rawLine.startsWith("data:")) continue;
            const payload = rawLine.replace("data:", "").trim();
            try {
              const parsed = JSON.parse(payload);
              if (parsed.message) {
                setLogs((previous) => [...previous, parsed as LogLine]);
              }
              if (parsed.status) {
                fetchJobs();
                fetchJobDetail(jobId);
              }
            } catch {
              // Ignore non-JSON stream fragments.
            }
          }
        }
      } catch (error: unknown) {
        if (!(error instanceof Error) || error.name !== "AbortError") {
          setLogs((previous) => [
            ...previous,
            {
              id: Date.now(),
              agent_name: "SYSTEM",
              log_level: "ERROR",
              message: getErrorMessage(error, "Log stream disconnected."),
              timestamp: new Date().toISOString(),
            },
          ]);
        }
      } finally {
        setStreamActive(false);
      }
    },
    [fetchJobDetail, fetchJobs, stopLogStream, token],
  );

  const submitScan = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!token) {
      setSubmitError("Connect a workspace before launching an audit.");
      return;
    }
    if (!repoUrl.trim()) {
      setSubmitError("Repository URL is required.");
      return;
    }

    setSubmitting(true);
    setSubmitError("");
    try {
      const response = await fetch(`${API_BASE_URL}/audit/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ repo_url: repoUrl.trim(), repo_branch: repoBranch.trim() || "main" }),
      });

      if (!response.ok) {
        const errorBody = await response.json();
        throw new Error(errorBody.detail || "Unable to launch audit.");
      }

      const job = (await response.json()) as Job;
      setRepoUrl("");
      setSelectedJobId(job.id);
      await fetchJobs();
      startLogStream(job.id);
    } catch (error: unknown) {
      setSubmitError(getErrorMessage(error, "Unable to launch audit."));
    } finally {
      setSubmitting(false);
    }
  };

  const cancelScan = async (jobId: string) => {
    if (!token) return;
    const response = await fetch(`${API_BASE_URL}/audit/job/${jobId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (response.ok) {
      fetchJobs();
      fetchJobDetail(jobId);
    }
  };

  useEffect(() => {
    const savedToken = localStorage.getItem("fc_token");
    const savedUsername = localStorage.getItem("fc_username");
    const savedUserId = localStorage.getItem("fc_user_id");

    if (savedToken && savedUsername && savedUserId) {
      setToken(savedToken);
      setUsername(savedUsername);
      setUserId(savedUserId);
      setAuthReady(true);
      return;
    }
    router.replace("/signin");
  }, [router]);

  const signOut = () => {
    stopLogStream();
    localStorage.removeItem("fc_token");
    localStorage.removeItem("fc_username");
    localStorage.removeItem("fc_user_id");
    localStorage.removeItem("fc_terms_accepted");
    router.push("/signin");
  };

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    fetchSystemStatus();
  }, [fetchSystemStatus]);

  useEffect(() => {
    if (!selectedJobId) return;
    fetchJobDetail(selectedJobId);
  }, [fetchJobDetail, selectedJobId]);

  useEffect(() => {
    if (!selectedJob) return;
    if (selectedJob.status === "queued" || selectedJob.status === "running") {
      const interval = window.setInterval(() => {
        fetchJobs();
        fetchJobDetail(selectedJob.id);
      }, 3500);
      return () => window.clearInterval(interval);
    }
  }, [fetchJobDetail, fetchJobs, selectedJob]);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const activeStep = selectedJob ? pipelineIndex(selectedJob.status, logs) : 0;

  if (!authReady) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <div className="section-kicker">Session</div>
          <h1>Opening FireCrow console</h1>
          <p>Checking for an authenticated Nova Devs workspace session.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">FC</div>
          <div>
            <div className="brand-name">FireCrow</div>
            <div className="brand-subtitle">FCv1 Security Audit</div>
          </div>
        </div>

        <nav className="nav-stack" aria-label="Primary navigation">
          {(["operations", "reports", "agents", "settings"] as Section[]).map((section) => (
            <button
              key={section}
              className={`nav-item ${activeSection === section ? "nav-item-active" : ""}`}
              type="button"
              aria-current={activeSection === section ? "page" : undefined}
              onClick={() => setActiveSection(section)}
            >
              {section}
            </button>
          ))}
        </nav>

        <div className="workspace-card">
          <div className="section-kicker">Workspace</div>
          <div className="workspace-name">{username || "Not connected"}</div>
          <div className="workspace-id">{userId || "Connect to access audit history"}</div>
        </div>
      </aside>

      <section className="main-surface">
        <header className="topbar">
          <div>
            <div className="section-kicker">Command Center</div>
            <h1>Security audit operations</h1>
          </div>
          <div className="workspace-session">
            <span>{username}</span>
            <button className="ghost-action" type="button" onClick={signOut}>
              Sign out
            </button>
          </div>
        </header>

        {activeSection === "operations" && (
          <>
        <section className="metrics-grid" aria-label="Audit metrics">
          <Metric label="Active audits" value={activeJobs.toString()} />
          <Metric label="Jobs in workspace" value={jobs.length.toString()} />
          <Metric label="Critical findings" value={criticalFindings.toString()} tone={criticalFindings > 0 ? "danger" : "neutral"} />
          <Metric label="Latest report" value={latestReport ? "Ready" : "None"} />
        </section>

        <section className="work-grid">
          <div className="panel launch-panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">New Audit</div>
                <h2>Repository intake</h2>
              </div>
            </div>

            <form onSubmit={submitScan} className="audit-form">
              <label>
                Repository URL
                <input
                  value={repoUrl}
                  onChange={(event) => setRepoUrl(event.target.value)}
                  placeholder="https://github.com/org/repository"
                />
              </label>
              <label>
                Branch or ref
                <input value={repoBranch} onChange={(event) => setRepoBranch(event.target.value)} placeholder="main" />
              </label>
              {submitError && <div className="notice notice-error">{submitError}</div>}
              <button className="primary-action" type="submit" disabled={submitting}>
                {submitting ? "Launching" : "Launch audit"}
              </button>
            </form>
          </div>

          <div className="panel queue-panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Queue</div>
                <h2>Audit history</h2>
              </div>
              <button className="ghost-action" type="button" onClick={fetchJobs} disabled={!token || loadingJobs}>
                Refresh
              </button>
            </div>

            <div className="job-list">
              {jobs.length === 0 ? (
                <div className="empty-state">No audits in this workspace.</div>
              ) : (
                jobs.map((job) => (
                  <button
                    key={job.id}
                    className={`job-row ${job.id === selectedJobId ? "job-row-active" : ""}`}
                    type="button"
                    onClick={() => {
                      setSelectedJobId(job.id);
                      fetchJobDetail(job.id);
                      startLogStream(job.id);
                    }}
                  >
                    <span>
                      <strong>{shortRepoName(job.repo_url)}</strong>
                      <small>{job.repo_branch} / {formatDateTime(job.created_at)}</small>
                    </span>
                    <span className={`status-pill status-${statusLabel(job)}`}>{statusLabel(job)}</span>
                  </button>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="detail-grid">
          <div className="panel pipeline-panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Maestro</div>
                <h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit selected"}</h2>
              </div>
              <div className="header-actions">
                {selectedJob?.report_pdf_url && (
                  <a className="ghost-action" href={selectedJob.report_pdf_url} target="_blank" rel="noreferrer">
                    Report
                  </a>
                )}
                {selectedJob && (selectedJob.status === "queued" || selectedJob.status === "running") && !selectedJob.cancel_requested && (
                  <button className="danger-action" type="button" onClick={() => cancelScan(selectedJob.id)}>
                    Cancel
                  </button>
                )}
              </div>
            </div>

            <div className="pipeline">
              {PIPELINE.map((phase, index) => (
                <div
                  key={phase}
                  className={`pipeline-step ${activeStep > index ? "pipeline-done" : ""} ${activeStep === index ? "pipeline-current" : ""}`}
                >
                  <span>{String(index).padStart(2, "0")}</span>
                  <strong>{phase}</strong>
                </div>
              ))}
            </div>

            {selectedJob && TERMINAL_STATUSES.includes(selectedJob.status) && selectedJob.error_message && (
              <div className="notice notice-error">{selectedJob.error_message}</div>
            )}
          </div>

          <div className="panel findings-panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">Findings</div>
                <h2>{loadingDetail ? "Loading" : `${findings.length} total`}</h2>
              </div>
            </div>

            <div className="finding-list">
              {findings.length === 0 ? (
                <div className="empty-state">No findings released for this audit.</div>
              ) : (
                findings.map((finding) => (
                  <article className="finding-row" key={finding.id}>
                    <div>
                      <span className={`severity severity-${finding.severity}`}>{finding.severity}</span>
                      <h3>{finding.title}</h3>
                      <p>{finding.description}</p>
                    </div>
                    <div className="finding-meta">
                      <span>{finding.agent_source}</span>
                      <strong>{finding.cvss_score ? finding.cvss_score.toFixed(1) : "CVSS -"}</strong>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="panel log-panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">Live Trace</div>
              <h2>Agent stream</h2>
            </div>
            <span className={`stream-state ${streamActive ? "stream-live" : ""}`}>{streamActive ? "live" : "idle"}</span>
          </div>

          <div className="log-list">
            {logs.length === 0 ? (
              <div className="empty-state">Select a running audit to stream logs.</div>
            ) : (
              logs.map((log) => (
                <div className="log-row" key={`${log.id}-${log.timestamp}`}>
                  <span>{formatDateTime(log.timestamp)}</span>
                  <strong>{log.agent_name}</strong>
                  <p>{log.message}</p>
                </div>
              ))
            )}
            <div ref={terminalEndRef} />
          </div>
        </section>
          </>
        )}

        {activeSection === "reports" && (
          <section className="section-body">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="section-kicker">Reports</div>
                  <h2>Released audit artifacts</h2>
                </div>
                <button className="ghost-action" type="button" onClick={fetchJobs} disabled={!token || loadingJobs}>
                  Refresh
                </button>
              </div>

              <div className="report-list">
                {!token ? (
                  <div className="empty-state">Connect a workspace to view reports.</div>
                ) : reportJobs.length === 0 ? (
                  <div className="empty-state">No terminal audit reports exist in this workspace yet.</div>
                ) : (
                  reportJobs.map((job) => (
                    <article className="report-row" key={job.id}>
                      <div>
                        <span className={`status-pill status-${statusLabel(job)}`}>{statusLabel(job)}</span>
                        <h3>{shortRepoName(job.repo_url)}</h3>
                        <p>
                          Branch {job.repo_branch} / finished {formatDateTime(job.finished_at)}
                        </p>
                      </div>
                      {job.report_pdf_url ? (
                        <a className="ghost-action" href={job.report_pdf_url} target="_blank" rel="noreferrer">
                          Open report
                        </a>
                      ) : (
                        <span className="report-missing">No PDF artifact</span>
                      )}
                    </article>
                  ))
                )}
              </div>
            </div>
          </section>
        )}

        {activeSection === "agents" && (
          <section className="section-body">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="section-kicker">Agents</div>
                  <h2>Runtime readiness</h2>
                </div>
                <button className="ghost-action" type="button" onClick={fetchSystemStatus} disabled={loadingSystem}>
                  Check status
                </button>
              </div>

              {systemError && <div className="notice notice-error">{systemError}</div>}

              <div className="agent-grid">
                {(systemStatus?.agents || []).map((agent) => (
                  <article className="agent-card" key={agent.name}>
                    <span className="stream-state stream-live">{agent.status}</span>
                    <h3>{agent.name}</h3>
                    <p>{agent.role}</p>
                  </article>
                ))}
                {!systemStatus && !systemError && (
                  <div className="empty-state">Checking backend agent readiness.</div>
                )}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="section-kicker">Maestro Topology</div>
                  <h2>Execution graph</h2>
                </div>
              </div>
              <div className="pipeline">
                {PIPELINE.map((phase, index) => (
                  <div key={phase} className="pipeline-step pipeline-current">
                    <span>{String(index).padStart(2, "0")}</span>
                    <strong>{phase}</strong>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {activeSection === "settings" && (
          <section className="section-body">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="section-kicker">Settings</div>
                  <h2>Backend and workspace status</h2>
                </div>
                <button className="ghost-action" type="button" onClick={fetchSystemStatus} disabled={loadingSystem}>
                  Refresh
                </button>
              </div>

              {systemError && <div className="notice notice-error">{systemError}</div>}

              <div className="settings-grid">
                <StatusCard label="API" value={systemStatus?.api || "checking"} tone={systemStatus?.api === "online" ? "good" : "warn"} />
                <StatusCard label="Database" value={systemStatus?.database || "checking"} tone={systemStatus?.database === "connected" ? "good" : "warn"} />
                <StatusCard label="Sandbox" value={systemStatus?.sandbox_mode === "docker" ? "Docker/Kali" : "Sandbox simulation"} tone="warn" />
                <StatusCard label="Workspace" value={username || "Not connected"} tone={username ? "good" : "warn"} />
              </div>

              <div className="integration-list">
                {Object.entries(systemStatus?.integrations || {}).map(([name, enabled]) => (
                  <div className="integration-row" key={name}>
                    <span>{name.replaceAll("_", " ")}</span>
                    <strong className={enabled ? "integration-on" : "integration-off"}>{enabled ? "configured" : "not configured"}</strong>
                  </div>
                ))}
                {!systemStatus && !systemError && (
                  <div className="empty-state">System status has not loaded yet.</div>
                )}
              </div>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "danger" }) {
  return (
    <div className={`metric metric-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusCard({ label, value, tone }: { label: string; value: string; tone: "good" | "warn" }) {
  return (
    <div className={`status-card status-card-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
