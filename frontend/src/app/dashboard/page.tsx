"use client";

import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield, Play, Square, RefreshCw, FileText, AlertTriangle, Terminal, Settings, LayoutGrid, Cpu, TrendingUp, LogOut, CheckCircle2, CheckCircle, Clock, XCircle, Search, HelpCircle, HardDrive, Database, Globe, Network, Fingerprint, Bug, User, ChevronRight, Download
} from "lucide-react";

import FireCrowLoader from "../../components/FireCrowLoader";
import {
  fadeIn,
  fadeInUp,
  fadeInRight,
  fadeInLeft,
  staggerContainer,
  scaleUp,
  tabTransition
} from "../../lib/animations";

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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

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
  const [reportError, setReportError] = useState("");
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

  const handleUnauthorized = useCallback(() => {
    localStorage.removeItem("fc_token");
    localStorage.removeItem("fc_username");
    localStorage.removeItem("fc_user_id");
    router.replace("/signin");
  }, [router]);

  const fetchSystemStatus = useCallback(async () => {
    if (!token) return;
    setLoadingSystem(true);
    setSystemError("");
    try {
      const response = await fetch(`${API_BASE_URL}/system/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 401 || response.status === 403) {
        handleUnauthorized();
        return;
      }
      if (!response.ok) {
        throw new Error("System status endpoint is unavailable.");
      }
      setSystemStatus((await response.json()) as SystemStatus);
    } catch (error: unknown) {
      setSystemError(getErrorMessage(error, "System status endpoint is unavailable."));
    } finally {
      setLoadingSystem(false);
    }
  }, [token, handleUnauthorized]);

  const openReport = useCallback(
    async (jobId: string) => {
      if (!token) return;
      setReportError("");
      try {
        const response = await fetch(`${API_BASE_URL}/audit/job/${jobId}/report`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.status === 401 || response.status === 403) {
          handleUnauthorized();
          return;
        }
        if (!response.ok) {
          const errorBody = await response.json().catch(() => null);
          throw new Error(errorBody?.detail || "Unable to open this report.");
        }

        const blob = await response.blob();
        const reportUrl = window.URL.createObjectURL(blob);
        window.open(reportUrl, "_blank", "noopener,noreferrer");
        window.setTimeout(() => window.URL.revokeObjectURL(reportUrl), 60_000);
      } catch (error: unknown) {
        setReportError(getErrorMessage(error, "Unable to open this report."));
      }
    },
    [token, handleUnauthorized],
  );

  const fetchJobs = useCallback(async () => {
    if (!token) return;
    setLoadingJobs(true);
    try {
      const response = await fetch(`${API_BASE_URL}/audit/jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 401 || response.status === 403) {
        handleUnauthorized();
        return;
      }
      if (response.ok) {
        const data = (await response.json()) as Job[];
        setJobs(data);
        setSelectedJobId((current) => current || data[0]?.id || null);
      }
    } finally {
      setLoadingJobs(false);
    }
  }, [token, handleUnauthorized]);

  const fetchJobDetail = useCallback(
    async (jobId: string) => {
      if (!token) return;
      setLoadingDetail(true);
      try {
        const response = await fetch(`${API_BASE_URL}/audit/job/${jobId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.status === 401 || response.status === 403) {
          handleUnauthorized();
          return;
        }
        if (response.ok) {
          setSelectedJobDetail((await response.json()) as JobDetail);
        }
      } finally {
        setLoadingDetail(false);
      }
    },
    [token, handleUnauthorized],
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

      if (response.status === 401 || response.status === 403) {
        handleUnauthorized();
        return;
      }

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
    if (response.status === 401 || response.status === 403) {
      handleUnauthorized();
      return;
    }
    if (response.ok) {
      fetchJobs();
      fetchJobDetail(jobId);
    }
  };

  useEffect(() => {
    const savedToken = localStorage.getItem("fc_token");
    const savedUsername = localStorage.getItem("fc_username");
    const savedUserId = localStorage.getItem("fc_user_id");

    if (!savedToken || !savedUsername || !savedUserId) {
      localStorage.removeItem("fc_token");
      localStorage.removeItem("fc_username");
      localStorage.removeItem("fc_user_id");
      router.replace("/signin");
      return;
    }

    const validateToken = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${savedToken}` },
        });
        if (response.status === 401 || response.status === 403) {
          localStorage.removeItem("fc_token");
          localStorage.removeItem("fc_username");
          localStorage.removeItem("fc_user_id");
          router.replace("/signin");
          return;
        }
        setToken(savedToken);
        setUsername(savedUsername);
        setUserId(savedUserId);
        setAuthReady(true);
      } catch (error) {
        // Fallback for network error / offline development
        setToken(savedToken);
        setUsername(savedUsername);
        setUserId(savedUserId);
        setAuthReady(true);
      }
    };

    void validateToken();
  }, [router, handleUnauthorized]);

  const signOut = () => {
    if (token) {
      void fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => undefined);
    }
    stopLogStream();
    localStorage.removeItem("fc_token");
    localStorage.removeItem("fc_username");
    localStorage.removeItem("fc_user_id");
    router.push("/signin");
  };

  useEffect(() => {
    if (!token) return;
    fetchJobs();
  }, [fetchJobs, token]);

  useEffect(() => {
    if (!token) return;
    fetchSystemStatus();
  }, [fetchSystemStatus, token]);

  useEffect(() => {
    if (!selectedJobId || !token) return;
    fetchJobDetail(selectedJobId);
  }, [fetchJobDetail, selectedJobId, token]);

  useEffect(() => {
    if (!selectedJob || !token) return;
    if (selectedJob.status === "queued" || selectedJob.status === "running") {
      const interval = window.setInterval(() => {
        fetchJobs();
        fetchJobDetail(selectedJob.id);
      }, 3500);
      return () => window.clearInterval(interval);
    }
  }, [fetchJobDetail, fetchJobs, selectedJob, token]);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const activeStep = selectedJob ? pipelineIndex(selectedJob.status, logs) : 0;

  const sectionIcon = (section: Section) => {
    switch (section) {
      case "operations": return <LayoutGrid className="nav-icon" size={16} />;
      case "reports": return <FileText className="nav-icon" size={16} />;
      case "agents": return <Cpu className="nav-icon" size={16} />;
      case "settings": return <Settings className="nav-icon" size={16} />;
    }
  };

  if (!authReady) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <FireCrowLoader size="lg" />
          <div className="section-kicker">Session</div>
          <h1>Opening FireCrow console</h1>
          <p>Checking for an authenticated Nova Devs workspace session.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      {/* Glow Orbs */}
      <div className="auth-glow-orb auth-glow-orb-1" style={{ opacity: 0.15 }} />
      <div className="auth-glow-orb auth-glow-orb-2" style={{ opacity: 0.15 }} />

      <motion.aside
        variants={fadeInLeft}
        initial="hidden"
        animate="visible"
        className="sidebar"
      >
        <div className="brand-block">
          <div className="brand-mark">FC</div>
          <div>
            <div className="brand-name">FireCrow</div>
            <div className="brand-subtitle">FCv1 Security Audit</div>
          </div>
        </div>

        <nav className="nav-stack" aria-label="Primary navigation">
          {(["operations", "reports", "agents", "settings"] as Section[]).map((section) => (
            <motion.button
              whileHover={{ x: 4, background: "rgba(255, 114, 0, 0.08)" }}
              whileTap={{ scale: 0.98 }}
              key={section}
              className={`nav-item ${activeSection === section ? "nav-item-active" : ""}`}
              type="button"
              aria-current={activeSection === section ? "page" : undefined}
              onClick={() => setActiveSection(section)}
            >
              {sectionIcon(section)}
              <span style={{ textTransform: "capitalize" }}>{section}</span>
            </motion.button>
          ))}
        </nav>

        <div className="workspace-card" style={{ position: "relative", overflow: "hidden" }}>
          <div className="auth-card-accent" />
          <div className="section-kicker">Workspace</div>
          <div className="workspace-name">{username || "Not connected"}</div>
          <div className="workspace-id" style={{ opacity: 0.5, fontSize: "10px" }}>{userId || "Connect to access audit history"}</div>
        </div>
      </motion.aside>

      <motion.section
        variants={fadeIn}
        initial="hidden"
        animate="visible"
        className="main-surface"
      >
        <header className="topbar">
          <div>
            <div className="section-kicker">Command Center</div>
            <h1 style={{ textTransform: "capitalize" }}>{activeSection}</h1>
          </div>
          <div className="workspace-session">
            <User size={13} style={{ color: "var(--fire)", marginRight: 2 }} />
            <span>{username}</span>
            <button className="ghost-action" type="button" onClick={signOut} style={{ height: "28px", minHeight: "28px", fontSize: "11px", padding: "0 8px" }}>
              <LogOut size={12} style={{ marginRight: 4 }} />
              Sign out
            </button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          {activeSection === "operations" && (
            <motion.div
              key="operations"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={staggerContainer}
            >
              <motion.section variants={fadeInUp} className="metrics-grid" aria-label="Audit metrics">
                <Metric label="Active audits" value={activeJobs.toString()} icon={<ActivityIcon />} />
                <Metric label="Jobs in workspace" value={jobs.length.toString()} icon={<Terminal size={18} />} />
                <Metric label="Critical findings" value={criticalFindings.toString()} tone={criticalFindings > 0 ? "danger" : "neutral"} icon={<AlertTriangle size={18} />} />
                <Metric label="Latest report" value={latestReport ? "Ready" : "None"} icon={<FileText size={18} />} />
              </motion.section>

              <div className="work-grid">
                <motion.div variants={scaleUp} className="panel launch-panel" style={{ position: "relative", overflow: "hidden" }}>
                  <div className="auth-card-accent" />
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
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="primary-action"
                      type="submit"
                      disabled={submitting}
                    >
                      {submitting ? <RefreshCw className="animate-spin" size={16} /> : <Play size={14} style={{ marginRight: 6 }} />}
                      {submitting ? "Launching" : "Launch audit"}
                    </motion.button>
                  </form>
                </motion.div>

                <motion.div variants={scaleUp} className="panel queue-panel">
                  <div className="panel-header">
                    <div>
                      <div className="section-kicker">Queue</div>
                      <h2>Audit history</h2>
                    </div>
                    <button className="ghost-action" type="button" onClick={fetchJobs} disabled={!token || loadingJobs} style={{ height: "30px", minHeight: "30px", fontSize: "11px" }}>
                      <RefreshCw className={loadingJobs ? "animate-spin" : ""} size={12} style={{ marginRight: 4 }} />
                      Refresh
                    </button>
                  </div>

                  <div className="job-list">
                    {jobs.length === 0 ? (
                      <div className="empty-state">No audits in this workspace.</div>
                    ) : (
                      jobs.map((job) => (
                        <motion.button
                          whileHover={{ scale: 1.01, x: 2 }}
                          whileTap={{ scale: 0.99 }}
                          key={job.id}
                          className={`job-row ${job.id === selectedJobId ? "job-row-active" : ""}`}
                          type="button"
                          onClick={() => {
                            setSelectedJobId(job.id);
                            fetchJobDetail(job.id);
                            startLogStream(job.id);
                          }}
                        >
                          <span style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <Terminal size={14} style={{ color: "var(--fire)" }} />
                            <span style={{ textAlign: "left" }}>
                              <strong>{shortRepoName(job.repo_url)}</strong>
                              <small>{job.repo_branch} / {formatDateTime(job.created_at)}</small>
                            </span>
                          </span>
                          <span className={`status-pill status-${statusLabel(job)}`}>{statusLabel(job)}</span>
                        </motion.button>
                      ))
                    )}
                  </div>
                </motion.div>
              </div>

              <div className="detail-grid">
                <motion.div variants={scaleUp} className="panel pipeline-panel">
                  <div className="panel-header">
                    <div>
                      <div className="section-kicker">Maestro</div>
                      <h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit selected"}</h2>
                    </div>
                    <div className="header-actions">
                      {selectedJob?.report_pdf_url && (
                        <button className="ghost-action" type="button" onClick={() => openReport(selectedJob.id)}>
                          <Download size={14} style={{ marginRight: 4 }} />
                          Report
                        </button>
                      )}
                      {selectedJob && (selectedJob.status === "queued" || selectedJob.status === "running") && !selectedJob.cancel_requested && (
                        <button className="danger-action" type="button" onClick={() => cancelScan(selectedJob.id)}>
                          <Square size={12} style={{ marginRight: 4 }} />
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
                  {reportError && <div className="notice notice-error">{reportError}</div>}
                </motion.div>

                <motion.div variants={scaleUp} className="panel findings-panel">
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
                        <motion.article whileHover={{ scale: 1.01 }} className="finding-row" key={finding.id}>
                          <div>
                            <span className={`severity severity-${finding.severity}`}>{finding.severity}</span>
                            <h3>{finding.title}</h3>
                            <p>{finding.description}</p>
                          </div>
                          <div className="finding-meta">
                            <span>{finding.agent_source}</span>
                            <strong>{finding.cvss_score ? finding.cvss_score.toFixed(1) : "CVSS -"}</strong>
                          </div>
                        </motion.article>
                      ))
                    )}
                  </div>
                </motion.div>
              </div>

              <motion.section variants={scaleUp} className="panel log-panel">
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
              </motion.section>
            </motion.div>
          )}

          {activeSection === "reports" && (
            <motion.div
              key="reports"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={tabTransition}
              className="section-body"
            >
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <div className="section-kicker">Reports</div>
                    <h2>Released audit artifacts</h2>
                  </div>
                  <button className="ghost-action" type="button" onClick={fetchJobs} disabled={!token || loadingJobs} style={{ height: "30px", minHeight: "30px", fontSize: "11px" }}>
                    <RefreshCw className={loadingJobs ? "animate-spin" : ""} size={12} style={{ marginRight: 4 }} />
                    Refresh
                  </button>
                </div>

                <div className="report-list">
                  {reportError && <div className="notice notice-error">{reportError}</div>}
                  {!token ? (
                    <div className="empty-state">Connect a workspace to view reports.</div>
                  ) : reportJobs.length === 0 ? (
                    <div className="empty-state">No terminal audit reports exist in this workspace yet.</div>
                  ) : (
                    reportJobs.map((job) => (
                      <motion.article whileHover={{ scale: 1.01 }} className="report-row" key={job.id}>
                        <div>
                          <span className={`status-pill status-${statusLabel(job)}`}>{statusLabel(job)}</span>
                          <h3>{shortRepoName(job.repo_url)}</h3>
                          <p>
                            Branch {job.repo_branch} / finished {formatDateTime(job.finished_at)}
                          </p>
                        </div>
                        {job.report_pdf_url ? (
                          <button className="ghost-action" type="button" onClick={() => openReport(job.id)}>
                            <FileText size={14} style={{ marginRight: 4 }} />
                            Open report
                          </button>
                        ) : (
                          <span className="report-missing">No PDF artifact</span>
                        )}
                      </motion.article>
                    ))
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {activeSection === "agents" && (
            <motion.div
              key="agents"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={tabTransition}
              className="section-body"
            >
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <div className="section-kicker">Agents</div>
                    <h2>Runtime readiness</h2>
                  </div>
                  <button className="ghost-action" type="button" onClick={fetchSystemStatus} disabled={loadingSystem} style={{ height: "30px", minHeight: "30px", fontSize: "11px" }}>
                    <RefreshCw className={loadingSystem ? "animate-spin" : ""} size={12} style={{ marginRight: 4 }} />
                    Check status
                  </button>
                </div>

                {systemError && <div className="notice notice-error">{systemError}</div>}

                <div className="agent-grid">
                  {(systemStatus?.agents || []).map((agent) => (
                    <motion.article whileHover={{ scale: 1.02, y: -2 }} className="agent-card" key={agent.name} style={{ position: "relative", overflow: "hidden" }}>
                      <div className="auth-card-accent" />
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                        <span className="stream-state stream-live" style={{ background: "rgba(0,230,118,0.1)", color: "var(--green)" }}>{agent.status}</span>
                        <Cpu size={16} style={{ color: "var(--fire)" }} />
                      </div>
                      <h3>{agent.name}</h3>
                      <p style={{ fontSize: "12px", color: "var(--dim)", marginTop: "4px" }}>{agent.role}</p>
                    </motion.article>
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
            </motion.div>
          )}

          {activeSection === "settings" && (
            <motion.div
              key="settings"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={tabTransition}
              className="section-body"
            >
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <div className="section-kicker">Settings</div>
                    <h2>Backend and workspace status</h2>
                  </div>
                  <button className="ghost-action" type="button" onClick={fetchSystemStatus} disabled={loadingSystem} style={{ height: "30px", minHeight: "30px", fontSize: "11px" }}>
                    <RefreshCw className={loadingSystem ? "animate-spin" : ""} size={12} style={{ marginRight: 4 }} />
                    Refresh
                  </button>
                </div>

                {systemError && <div className="notice notice-error">{systemError}</div>}

                <div className="settings-grid">
                  <StatusCard label="API" value={systemStatus?.api || "checking"} tone={systemStatus?.api === "online" ? "good" : "warn"} icon={<Globe size={14} />} />
                  <StatusCard label="Database" value={systemStatus?.database || "checking"} tone={systemStatus?.database === "connected" ? "good" : "warn"} icon={<Database size={14} />} />
                  <StatusCard label="Sandbox" value={systemStatus?.sandbox_mode === "docker" ? "Docker/Kali" : "Sandbox simulation"} tone="warn" icon={<HardDrive size={14} />} />
                  <StatusCard label="Workspace" value={username || "Not connected"} tone={username ? "good" : "warn"} icon={<Fingerprint size={14} />} />
                </div>

                <div className="integration-list" style={{ marginTop: "20px" }}>
                  {Object.entries(systemStatus?.integrations || {}).map(([name, enabled]) => (
                    <motion.div whileHover={{ x: 2 }} className="integration-row" key={name} style={{ display: "flex", justifyContent: "space-between", padding: "12px 14px", borderBottom: "1px solid var(--border)" }}>
                      <span style={{ textTransform: "capitalize" }}>{name.replaceAll("_", " ")}</span>
                      <strong className={enabled ? "integration-on" : "integration-off"}>{enabled ? "configured" : "not configured"}</strong>
                    </motion.div>
                  ))}
                  {!systemStatus && !systemError && (
                    <div className="empty-state">System status has not loaded yet.</div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.section>
    </main>
  );
}

function ActivityIcon() {
  return (
    <span style={{ display: "inline-flex", width: "10px", height: "10px", borderRadius: "50%", background: "var(--green)", position: "relative" }}>
      <span className="animate-ping" style={{ position: "absolute", display: "inline-flex", height: "100%", width: "100%", borderRadius: "50%", background: "var(--green)", opacity: 0.75 }} />
    </span>
  );
}

function Metric({ label, value, tone = "neutral", icon }: { label: string; value: string; tone?: "neutral" | "danger"; icon?: React.ReactNode }) {
  return (
    <div className={`metric metric-${tone}`} style={{ position: "relative", overflow: "hidden", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <div className="auth-card-accent" />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
    </div>
  );
}

function StatusCard({ label, value, tone, icon }: { label: string; value: string; tone: "good" | "warn"; icon?: React.ReactNode }) {
  return (
    <div className={`status-card status-card-${tone}`} style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", padding: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>{label}</span>
        {icon}
      </div>
      <strong style={{ fontSize: "18px", marginTop: "12px", display: "block" }}>{value}</strong>
    </div>
  );
}
