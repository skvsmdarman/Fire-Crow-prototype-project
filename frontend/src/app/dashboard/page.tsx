"use client";

import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  RefreshCw, FileText, Cpu, LogOut, HardDrive, Database, Globe, Fingerprint, User
} from "lucide-react";

import FireCrowLoader from "../../components/FireCrowLoader";
import { useToast } from "../../components/ui/Toast";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";

import Sidebar, { Section } from "./components/Sidebar";
import MetricsRow from "./components/MetricsRow";
import AuditForm from "./components/AuditForm";
import JobList from "./components/JobList";
import PipelineViz from "./components/PipelineViz";
import FindingsList from "./components/FindingsList";
import LogStream from "./components/LogStream";

import {
  fadeIn,
  fadeInUp,
  staggerContainer,
  scaleUp,
  tabTransition
} from "../../lib/animations";
import styles from "./page.module.css";

type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled" | "partial";
type Severity = "critical" | "high" | "medium" | "low" | "info";

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
const TERMINAL_STATUSES: JobStatus[] = ["completed", "failed", "cancelled", "partial"];
const TABS: Section[] = ["operations", "reports", "agents", "settings"];

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

function statusLabel(job: Job): "queued" | "running" | "completed" | "failed" | "cancelled" | "partial" | "cancelling" {
  if (job.cancel_requested && !TERMINAL_STATUSES.includes(job.status)) {
    return "cancelling";
  }
  return job.status;
}

function pipelineIndex(status: JobStatus, logs: LogLine[]): number {
  if (status === "queued") return 0;
  if (status === "completed" || status === "partial") return 9; // CLEANUP
  if (status === "failed" || status === "cancelled") return -1;

  let index = 1; // STATIC SCAN
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
  const { toast } = useToast();

  const [activeSection, setActiveSection] = useState<Section>("operations");
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [userId, setUserId] = useState("");
  const [authReady, setAuthReady] = useState(false);

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

  // Touch Swipe Gesture State
  const touchStartXRef = useRef<number | null>(null);

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
    toast("Session expired. Please sign in again.", "error");
  }, [router, toast]);

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
      toast("Retrieving report PDF...", "info");
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
        toast("Report opened successfully.", "success");
      } catch (error: unknown) {
        const msg = getErrorMessage(error, "Unable to open this report.");
        setReportError(msg);
        toast(msg, "error");
      }
    },
    [token, handleUnauthorized, toast],
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

  const handleLaunchScan = async (repoUrl: string, repoBranch: string) => {
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
    toast("Submitting repository intake request...", "info");
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
      setSelectedJobId(job.id);
      await fetchJobs();
      startLogStream(job.id);
      toast("Audit job successfully queued!", "success");
    } catch (error: unknown) {
      const msg = getErrorMessage(error, "Unable to launch audit.");
      setSubmitError(msg);
      toast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const cancelScan = async (jobId: string) => {
    if (!token) return;
    toast("Requesting job cancellation...", "info");
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
      toast("Cancellation request transmitted.", "success");
    } else {
      toast("Unable to cancel job.", "error");
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
      } catch {
        // Clear session and redirect to signin if backend is unreachable
        localStorage.removeItem("fc_token");
        localStorage.removeItem("fc_username");
        localStorage.removeItem("fc_user_id");
        router.replace("/signin");
      }
    };

    void validateToken();
  }, [router]);

  const signOut = () => {
    toast("Signing out...", "info");
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

  const activeStep = selectedJob ? pipelineIndex(selectedJob.status, logs) : 0;

  // Swipe Gesture Handlers
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartXRef.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartXRef.current === null) return;
    const touchEndX = e.changedTouches[0].clientX;
    const diffX = touchStartXRef.current - touchEndX;
    const currentTabIndex = TABS.indexOf(activeSection);

    if (Math.abs(diffX) > 72) {
      if (diffX > 0) {
        // Swiped Left -> Next tab
        if (currentTabIndex < TABS.length - 1) {
          const nextTab = TABS[currentTabIndex + 1];
          setActiveSection(nextTab);
          toast(`Navigated to ${nextTab}`, "info");
        }
      } else {
        // Swiped Right -> Previous tab
        if (currentTabIndex > 0) {
          const prevTab = TABS[currentTabIndex - 1];
          setActiveSection(prevTab);
          toast(`Navigated to ${prevTab}`, "info");
        }
      }
    }
    touchStartXRef.current = null;
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
    <main className={styles.shell}>
      {/* Glow Orbs */}
      <div className="auth-glow-orb auth-glow-orb-1" style={{ opacity: 0.15 }} />
      <div className="auth-glow-orb auth-glow-orb-2" style={{ opacity: 0.15 }} />

      <Sidebar
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        username={username}
        userId={userId}
      />

      <motion.section
        variants={fadeIn}
        initial="hidden"
        animate="visible"
        className={styles.mainSurface}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <header className={styles.topbar}>
          <div>
            <div className={styles.sectionKicker}>Command Center</div>
            <h1>{activeSection}</h1>
          </div>
          <div className={styles.workspaceSession}>
            <User size={13} style={{ color: "var(--fire)", marginRight: 2 }} />
            <span>{username}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={signOut}
              style={{ minHeight: "28px", fontSize: "11px", padding: "0 8px" }}
            >
              <LogOut size={12} />
              Sign out
            </Button>
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
              <motion.div variants={fadeInUp}>
                <MetricsRow
                  activeAudits={activeJobs}
                  totalJobs={jobs.length}
                  criticalFindings={criticalFindings}
                  latestReport={latestReport}
                />
              </motion.div>

              <div className={styles.workGrid}>
                <motion.div variants={scaleUp}>
                  <AuditForm
                    onSubmit={handleLaunchScan}
                    submitting={submitting}
                    submitError={submitError}
                  />
                </motion.div>

                <motion.div variants={scaleUp}>
                  <JobList
                    jobs={jobs}
                    selectedJobId={selectedJobId}
                    loadingJobs={loadingJobs}
                    onRefresh={fetchJobs}
                    onJobSelect={(jobId) => {
                      setSelectedJobId(jobId);
                      fetchJobDetail(jobId);
                      startLogStream(jobId);
                    }}
                  />
                </motion.div>
              </div>

              <div className={styles.detailGrid}>
                <motion.div variants={scaleUp}>
                  <PipelineViz
                    job={selectedJob}
                    activeStep={activeStep}
                    onOpenReport={openReport}
                    onCancel={cancelScan}
                    reportError={reportError}
                  />
                </motion.div>

                <motion.div variants={scaleUp}>
                  <FindingsList findings={findings} loading={loadingDetail} />
                </motion.div>
              </div>

              <motion.div variants={scaleUp}>
                <LogStream logs={logs} streamActive={streamActive} />
              </motion.div>
            </motion.div>
          )}

          {activeSection === "reports" && (
            <motion.div
              key="reports"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={tabTransition}
              className={styles.sectionBody}
            >
              <Card variant="surface" className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <div className={styles.sectionKicker}>Reports</div>
                    <h2>Released audit artifacts</h2>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={fetchJobs}
                    disabled={!token || loadingJobs}
                  >
                    <RefreshCw className={loadingJobs ? styles.spin : ""} size={12} />
                    Refresh
                  </Button>
                </div>

                <div className={styles.reportList}>
                  {reportError && <div className={styles.noticeError}>{reportError}</div>}
                  {!token ? (
                    <div className={styles.emptyState}>Connect a workspace to view reports.</div>
                  ) : reportJobs.length === 0 ? (
                    <div className={styles.emptyState}>
                      No terminal audit reports exist in this workspace yet.
                    </div>
                  ) : (
                    reportJobs.map((job) => (
                      <motion.article
                        whileHover={{ scale: 1.01 }}
                        className={styles.reportRow}
                        key={job.id}
                      >
                        <div>
                          <Badge variant="status" type={statusLabel(job)}>
                            {statusLabel(job)}
                          </Badge>
                          <h3>{shortRepoName(job.repo_url)}</h3>
                          <p>
                            Branch {job.repo_branch} / finished {formatDateTime(job.finished_at)}
                          </p>
                        </div>
                        {job.report_pdf_url ? (
                          <Button variant="ghost" size="sm" onClick={() => openReport(job.id)}>
                            <FileText size={14} />
                            Open report
                          </Button>
                        ) : (
                          <span className={styles.reportMissing}>No PDF artifact</span>
                        )}
                      </motion.article>
                    ))
                  )}
                </div>
              </Card>
            </motion.div>
          )}

          {activeSection === "agents" && (
            <motion.div
              key="agents"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={tabTransition}
              className={styles.sectionBody}
            >
              <Card variant="surface" className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <div className={styles.sectionKicker}>Agents</div>
                    <h2>Runtime readiness</h2>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={fetchSystemStatus}
                    disabled={loadingSystem}
                  >
                    <RefreshCw className={loadingSystem ? styles.spin : ""} size={12} />
                    Check status
                  </Button>
                </div>

                {systemError && <div className={styles.noticeError}>{systemError}</div>}

                <div className={styles.agentGrid}>
                  {(systemStatus?.agents || []).map((agent) => (
                    <motion.article
                      whileHover={{ scale: 1.02, y: -2 }}
                      className={styles.agentCard}
                      key={agent.name}
                    >
                      <div className={styles.authCardAccent} />
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                          marginBottom: 12,
                        }}
                      >
                        <Badge variant="simple" type="live" pulse>
                          {agent.status}
                        </Badge>
                        <Cpu size={16} style={{ color: "var(--fire)" }} />
                      </div>
                      <h3>{agent.name}</h3>
                      <p style={{ fontSize: "12px", color: "var(--dim)", marginTop: "4px" }}>
                        {agent.role}
                      </p>
                    </motion.article>
                  ))}
                  {!systemStatus && !systemError && (
                    <div className={styles.emptyState}>Checking backend agent readiness.</div>
                  )}
                </div>
              </Card>
            </motion.div>
          )}

          {activeSection === "settings" && (
            <motion.div
              key="settings"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={tabTransition}
              className={styles.sectionBody}
            >
              <Card variant="surface" className={styles.panel}>
                <div className={styles.panelHeader}>
                  <div>
                    <div className={styles.sectionKicker}>Settings</div>
                    <h2>Backend and workspace status</h2>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={fetchSystemStatus}
                    disabled={loadingSystem}
                  >
                    <RefreshCw className={loadingSystem ? styles.spin : ""} size={12} />
                    Refresh
                  </Button>
                </div>

                {systemError && <div className={styles.noticeError}>{systemError}</div>}

                <div className={styles.settingsGrid}>
                  <StatusCard
                    label="API"
                    value={systemStatus?.api || "checking"}
                    tone={systemStatus?.api === "online" ? "good" : "warn"}
                    icon={<Globe size={14} />}
                  />
                  <StatusCard
                    label="Database"
                    value={systemStatus?.database || "checking"}
                    tone={systemStatus?.database === "connected" ? "good" : "warn"}
                    icon={<Database size={14} />}
                  />
                  <StatusCard
                    label="Sandbox"
                    value={systemStatus?.sandbox_mode === "docker" ? "Docker/Kali" : "Simulation"}
                    tone="warn"
                    icon={<HardDrive size={14} />}
                  />
                  <StatusCard
                    label="Workspace"
                    value={username || "Not connected"}
                    tone={username ? "good" : "warn"}
                    icon={<Fingerprint size={14} />}
                  />
                </div>

                <div className={styles.integrationList}>
                  {Object.entries(systemStatus?.integrations || {}).map(([name, enabled]) => (
                    <motion.div
                      whileHover={{ x: 2 }}
                      className={styles.integrationRow}
                      key={name}
                    >
                      <span>{name.replaceAll("_", " ")}</span>
                      <strong className={enabled ? styles.integrationOn : styles.integrationOff}>
                        {enabled ? "configured" : "not configured"}
                      </strong>
                    </motion.div>
                  ))}
                  {!systemStatus && !systemError && (
                    <div className={styles.emptyState}>System status has not loaded yet.</div>
                  )}
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.section>
    </main>
  );
}

function StatusCard({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: string;
  tone: "good" | "warn";
  icon?: React.ReactNode;
}) {
  const cardClass = [
    styles.statusCard,
    tone === "good" ? styles.statusCardGood : styles.statusCardWarn,
  ].join(" ");

  return (
    <div className={cardClass}>
      <div className={styles.statusCardHeader}>
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
    </div>
  );
}
