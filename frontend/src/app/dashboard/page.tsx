"use client";

import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Database,
  Download,
  FileText,
  Fingerprint,
  Globe,
  HardDrive,
  LogOut,
  Play,
  PlusCircle,
  RefreshCw,
  Search,
  ShieldCheck,
  User,
} from "lucide-react";

import FireCrowLoader from "../../components/FireCrowLoader";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import { useToast } from "../../components/ui/Toast";
import { fadeIn, fadeInUp, scaleUp, staggerContainer, tabTransition } from "../../lib/animations";
import { clearStoredAuthSession, getStoredAuthSession } from "../../lib/authSession";
import AuditForm from "./components/AuditForm";
import FindingsList from "./components/FindingsList";
import JobList from "./components/JobList";
import LogStream from "./components/LogStream";
import MetricsRow from "./components/MetricsRow";
import PipelineViz from "./components/PipelineViz";
import Sidebar, { Section } from "./components/Sidebar";
import mobile from "./mobile.module.css";
import styles from "./page.module.css";
import { API_BASE_URL } from "../../lib/policy";

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
  stats: { jobs: number; findings: number };
  integrations: Record<string, boolean>;
  agents: SystemAgent[];
}

const TERMINAL_STATUSES: JobStatus[] = ["completed", "failed", "cancelled", "partial"];
const TABS: Section[] = ["home", "audits", "findings", "reports", "settings"];
const SECTION_TITLES: Record<Section, string> = {
  home: "Overview",
  audits: "Audits",
  findings: "Findings",
  reports: "Reports",
  settings: "Settings",
};

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function sanitizeRepoUrl(repoUrl: string): string {
  return repoUrl.replace(/\/\/([^/@\s]+)@/, "//***@");
}

function shortRepoName(repoUrl: string): string {
  return sanitizeRepoUrl(repoUrl).replace(/^https:\/\/github\.com\//, "").replace(/\/$/, "");
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
  if (job.cancel_requested && !TERMINAL_STATUSES.includes(job.status)) return "cancelling";
  return job.status;
}

function calculateRiskScore(findings: Finding[]): number | null {
  if (findings.length === 0) return null;
  const weights: Record<Severity, number> = { critical: 28, high: 18, medium: 9, low: 4, info: 0 };
  return Math.min(100, findings.reduce((score, finding) => score + weights[finding.severity], 0));
}

function postureLabel(score: number | null, activeJobs: number): string {
  if (activeJobs > 0) return "Audit running";
  if (score === null) return "Awaiting first audit";
  if (score >= 80) return "Critical attention";
  if (score >= 55) return "High risk";
  if (score >= 25) return "Needs review";
  return "Controlled";
}

function severityBreakdown(findings: Finding[]) {
  return findings.reduce<Record<Severity, number>>(
    (acc, finding) => {
      acc[finding.severity] += 1;
      return acc;
    },
    { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
  );
}

export default function Dashboard() {
  const router = useRouter();
  const { toast } = useToast();
  const [activeSection, setActiveSection] = useState<Section>("home");
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
  const touchStartXRef = useRef<number | null>(null);

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) || selectedJobDetail?.job || null,
    [jobs, selectedJobDetail, selectedJobId],
  );

  const findings = selectedJobDetail?.findings || [];
  const activeJobs = jobs.filter((job) => job.status === "queued" || job.status === "running").length;
  const criticalFindings = findings.filter((finding) => finding.severity === "critical").length;
  const highFindings = findings.filter((finding) => finding.severity === "high").length;
  const latestReportJob = jobs.find((job) => job.report_pdf_url) || null;
  const latestReport = latestReportJob?.report_pdf_url || null;
  const reportJobs = jobs.filter((job) => TERMINAL_STATUSES.includes(job.status));
  const riskScore = calculateRiskScore(findings);
  const posture = postureLabel(riskScore, activeJobs);
  const severityCounts = severityBreakdown(findings);
  const recentJobs = jobs.slice(0, 4);

  const handleUnauthorized = useCallback(() => {
    clearStoredAuthSession();
    const searchParamsString = typeof window !== "undefined" ? window.location.search : "";
    router.replace(`/signin${searchParamsString}`);
    toast("Session expired. Please sign in again.", "error");
  }, [router, toast]);

  const fetchSystemStatus = useCallback(async () => {
    if (!token) return;
    setLoadingSystem(true);
    setSystemError("");
    try {
      const response = await fetch(`${API_BASE_URL}/system/status`, { headers: { Authorization: `Bearer ${token}` } });
      if (response.status === 401 || response.status === 403) return handleUnauthorized();
      if (!response.ok) throw new Error("System status endpoint is unavailable.");
      setSystemStatus((await response.json()) as SystemStatus);
    } catch (error: unknown) {
      setSystemError(getErrorMessage(error, "System status endpoint is unavailable."));
    } finally {
      setLoadingSystem(false);
    }
  }, [handleUnauthorized, token]);

  const fetchJobs = useCallback(async () => {
    if (!token) return;
    setLoadingJobs(true);
    try {
      const response = await fetch(`${API_BASE_URL}/audit/jobs`, { headers: { Authorization: `Bearer ${token}` } });
      if (response.status === 401 || response.status === 403) return handleUnauthorized();
      if (response.ok) {
        const data = (await response.json()) as Job[];
        setJobs(data);
        setSelectedJobId((current) => current || data[0]?.id || null);
      }
    } finally {
      setLoadingJobs(false);
    }
  }, [handleUnauthorized, token]);

  const fetchJobDetail = useCallback(
    async (jobId: string) => {
      if (!token) return;
      setLoadingDetail(true);
      try {
        const response = await fetch(`${API_BASE_URL}/audit/job/${jobId}`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401 || response.status === 403) return handleUnauthorized();
        if (response.ok) setSelectedJobDetail((await response.json()) as JobDetail);
      } finally {
        setLoadingDetail(false);
      }
    },
    [handleUnauthorized, token],
  );

  const [selectedRepoUrl, setSelectedRepoUrl] = useState<string | null>(null);

  const uniqueRepos = useMemo(() => {
    const seen = new Set<string>();
    const repos: { url: string; name: string }[] = [];
    for (const job of jobs) {
      if (!seen.has(job.repo_url)) {
        seen.add(job.repo_url);
        repos.push({ url: job.repo_url, name: shortRepoName(job.repo_url) });
      }
    }
    return repos;
  }, [jobs]);

  const currentRepoUrl = selectedJob?.repo_url || selectedRepoUrl || (uniqueRepos[0]?.url) || null;

  const repoRuns = useMemo(() => {
    if (!currentRepoUrl) return [];
    return jobs.filter((job) => job.repo_url === currentRepoUrl);
  }, [jobs, currentRepoUrl]);

  const handleRepoChange = useCallback((repoUrl: string) => {
    setSelectedRepoUrl(repoUrl);
    const runs = jobs.filter((j) => j.repo_url === repoUrl);
    if (runs.length > 0) {
      setSelectedJobId(runs[0].id);
      fetchJobDetail(runs[0].id);
    }
  }, [jobs, fetchJobDetail]);

  useEffect(() => {
    if (selectedJob && selectedJob.repo_url !== selectedRepoUrl) {
      setSelectedRepoUrl(selectedJob.repo_url);
    }
  }, [selectedJob, selectedRepoUrl]);

  const openReport = useCallback(
    async (jobId: string) => {
      if (!token) return;
      setReportError("");
      toast("Retrieving report PDF...", "info");
      try {
        const response = await fetch(`${API_BASE_URL}/audit/job/${jobId}/report`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401 || response.status === 403) return handleUnauthorized();
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
    [handleUnauthorized, toast, token],
  );

  const stopLogStream = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
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
        if (response.status === 401 || response.status === 403) return handleUnauthorized();
        if (!response.body) throw new Error("Log stream unavailable.");
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
              if (parsed.message) setLogs((previous) => [...previous, parsed as LogLine]);
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
            { id: Date.now(), agent_name: "SYSTEM", log_level: "ERROR", message: getErrorMessage(error, "Log stream disconnected."), timestamp: new Date().toISOString() },
          ]);
        }
      } finally {
        setStreamActive(false);
      }
    },
    [fetchJobDetail, fetchJobs, handleUnauthorized, stopLogStream, token],
  );

  const handleLaunchScan = async (repoUrl: string, repoBranch: string) => {
    if (!token) return setSubmitError("Connect a workspace before launching an audit.");
    if (!repoUrl.trim()) return setSubmitError("Repository URL is required.");
    setSubmitting(true);
    setSubmitError("");
    toast("Submitting repository intake request...", "info");
    try {
      const response = await fetch(`${API_BASE_URL}/audit/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ repo_url: repoUrl.trim(), repo_branch: repoBranch.trim() || "main" }),
      });
      if (response.status === 401 || response.status === 403) return handleUnauthorized();
      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        throw new Error(errorBody?.detail || "Unable to launch audit.");
      }
      const job = (await response.json()) as Job;
      setSelectedJobId(job.id);
      setActiveSection("audits");
      await fetchJobs();
      toast("Audit job successfully queued!", "success");
    } catch (error: unknown) {
      const msg = getErrorMessage(error, "Unable to launch audit.");
      setSubmitError(msg);
      toast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLaunchBulkScan = async (repoUrls: string[], repoBranch: string) => {
    if (!token) return setSubmitError("Connect a workspace before launching an audit.");
    if (!repoUrls.length) return setSubmitError("At least one repository URL is required.");
    setSubmitting(true);
    setSubmitError("");
    toast(`Submitting ${repoUrls.length} repository intake requests...`, "info");
    try {
      const response = await fetch(`${API_BASE_URL}/audit/submit-bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ repo_urls: repoUrls, repo_branch: repoBranch.trim() || "main" }),
      });
      if (response.status === 401 || response.status === 403) return handleUnauthorized();
      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        throw new Error(errorBody?.detail || "Unable to launch bulk audits.");
      }
      const queuedJobs = (await response.json()) as Job[];
      if (queuedJobs.length > 0) {
        setSelectedJobId(queuedJobs[0].id);
      }
      setActiveSection("audits");
      await fetchJobs();
      toast(`Successfully queued ${queuedJobs.length} audit jobs!`, "success");
    } catch (error: unknown) {
      const msg = getErrorMessage(error, "Unable to launch bulk audits.");
      setSubmitError(msg);
      toast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const cancelScan = async (jobId: string) => {
    if (!token) return;
    toast("Requesting job cancellation...", "info");
    const response = await fetch(`${API_BASE_URL}/audit/job/${jobId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    if (response.status === 401 || response.status === 403) return handleUnauthorized();
    if (response.ok) {
      fetchJobs();
      fetchJobDetail(jobId);
      toast("Cancellation request transmitted.", "success");
    } else {
      toast("Unable to cancel job.", "error");
    }
  };

  const signOut = () => {
    toast("Signing out...", "info");
    if (token) void fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => undefined);
    stopLogStream();
    clearStoredAuthSession();
    router.push("/signin");
  };

  useEffect(() => {
    const { token: savedToken, userId: savedUserId, username: savedUsername } = getStoredAuthSession();
    if (!savedToken || !savedUsername || !savedUserId) {
      clearStoredAuthSession();
      const searchParamsString = typeof window !== "undefined" ? window.location.search : "";
      router.replace(`/signin${searchParamsString}`);
      return;
    }
    const validateToken = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, { headers: { Authorization: `Bearer ${savedToken}` } });
        if (response.status === 401 || response.status === 403) {
          clearStoredAuthSession();
          const searchParamsString = typeof window !== "undefined" ? window.location.search : "";
          router.replace(`/signin${searchParamsString}`);
          return;
        }
        setToken(savedToken);
        setUsername(savedUsername);
        setUserId(savedUserId);
        setAuthReady(true);
      } catch {
        clearStoredAuthSession();
        const searchParamsString = typeof window !== "undefined" ? window.location.search : "";
        router.replace(`/signin${searchParamsString}`);
      }
    };
    void validateToken();
  }, [router]);

  useEffect(() => { if (token) fetchJobs(); }, [fetchJobs, token]);
  useEffect(() => { if (token) fetchSystemStatus(); }, [fetchSystemStatus, token]);
  useEffect(() => { if (selectedJobId && token) fetchJobDetail(selectedJobId); }, [fetchJobDetail, selectedJobId, token]);
  useEffect(() => {
    if (!token || !selectedJobId || activeSection !== "audits") {
      stopLogStream();
      return;
    }

    void startLogStream(selectedJobId);
    return stopLogStream;
  }, [activeSection, selectedJobId, startLogStream, stopLogStream, token]);

  useEffect(() => {
    if (typeof window === "undefined" || !token || !authReady) return;
    const urlParams = new URLSearchParams(window.location.search);
    const queryJobId = urlParams.get("job_id");
    if (queryJobId) {
      setSelectedJobId(queryJobId);
      setActiveSection("reports");
      openReport(queryJobId);
      // Clean up the URL to prevent double opening on refresh
      const url = new URL(window.location.href);
      url.searchParams.delete("job_id");
      window.history.replaceState({}, "", url.toString());
    }
  }, [token, authReady, openReport]);
  useEffect(() => {
    if (!selectedJob || !token || (selectedJob.status !== "queued" && selectedJob.status !== "running")) return;
    const interval = window.setInterval(() => {
      fetchJobs();
      fetchJobDetail(selectedJob.id);
    }, 3500);
    return () => window.clearInterval(interval);
  }, [fetchJobDetail, fetchJobs, selectedJob, token]);
  const onTouchStart = (event: React.TouchEvent) => { touchStartXRef.current = event.touches[0].clientX; };
  const onTouchEnd = (event: React.TouchEvent) => {
    if (touchStartXRef.current === null) return;
    const diffX = touchStartXRef.current - event.changedTouches[0].clientX;
    const currentTabIndex = TABS.indexOf(activeSection);
    if (Math.abs(diffX) > 72 && diffX > 0 && currentTabIndex < TABS.length - 1) setActiveSection(TABS[currentTabIndex + 1]);
    if (Math.abs(diffX) > 72 && diffX < 0 && currentTabIndex > 0) setActiveSection(TABS[currentTabIndex - 1]);
    touchStartXRef.current = null;
  };

  if (!authReady) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <FireCrowLoader size="lg" />
          <div className="section-kicker">Session</div>
          <h1>Opening Fire Crow console</h1>
          <p>Checking for an authenticated workspace session.</p>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <div className="auth-glow-orb auth-glow-orb-1" style={{ opacity: 0.15 }} />
      <div className="auth-glow-orb auth-glow-orb-2" style={{ opacity: 0.15 }} />
      <Sidebar activeSection={activeSection} setActiveSection={setActiveSection} username={username} userId={userId} />

      <motion.section variants={fadeIn} initial="hidden" animate="visible" className={styles.mainSurface} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        <header className={styles.topbar}>
          <div>
            <div className={styles.sectionKicker}>Fire Crow workspace</div>
            <h1>{SECTION_TITLES[activeSection]}</h1>
          </div>
          <div className={styles.workspaceSession}>
            <User size={13} className={styles.sessionIcon} />
            <div className={styles.sessionMeta}>
              <strong>{username}</strong>
              <span>Signed in</span>
            </div>
            <Button variant="ghost" size="sm" onClick={signOut} style={{ minHeight: "32px", fontSize: "11px", padding: "0 8px" }}><LogOut size={12} />Sign out</Button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          {activeSection === "home" && (
            <motion.div key="home" initial="hidden" animate="visible" exit="exit" variants={staggerContainer}>
              <motion.div variants={fadeInUp}><MetricsRow activeAudits={activeJobs} totalJobs={jobs.length} criticalFindings={criticalFindings} latestReport={latestReport} /></motion.div>
              <div className={mobile.homeGrid}>
                <div className={mobile.homePrimary}>
                  <motion.div variants={scaleUp}>
                    <Card variant="surface" className={`${styles.panel} ${mobile.overviewCard}`}>
                      <div className={styles.panelHeader} style={{ flexWrap: "wrap", gap: "12px" }}>
                        <div style={{ flexGrow: 1, minWidth: "200px" }}>
                          <div className={styles.sectionKicker}>Current view</div>
                          <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "4px" }}>
                            <h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit selected"}</h2>
                             {uniqueRepos.length > 0 && (
                              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "4px" }}>
                                <div style={{ display: "flex", flexDirection: "column", gap: "2px", flexGrow: 1, minWidth: "140px" }}>
                                  <label style={{ fontSize: "10px", color: "var(--muted)", fontWeight: 700, textTransform: "uppercase" }}>Repository</label>
                                  <select
                                    value={currentRepoUrl || ""}
                                    onChange={(e) => handleRepoChange(e.target.value)}
                                    className={styles.customSelect}
                                    style={{ maxWidth: "280px", padding: "8px 12px" }}
                                  >
                                    {uniqueRepos.map((repo) => (
                                      <option key={repo.url} value={repo.url} className={styles.customSelectOption}>
                                        {repo.name}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                                <div style={{ display: "flex", flexDirection: "column", gap: "2px", flexGrow: 1, minWidth: "140px" }}>
                                  <label style={{ fontSize: "10px", color: "var(--muted)", fontWeight: 700, textTransform: "uppercase" }}>Run History</label>
                                  <select
                                    value={selectedJobId || ""}
                                    onChange={(e) => {
                                      const jobId = e.target.value;
                                      setSelectedJobId(jobId);
                                      fetchJobDetail(jobId);
                                    }}
                                    className={styles.customSelect}
                                    style={{ maxWidth: "280px", padding: "8px 12px" }}
                                  >
                                    {repoRuns.map((run) => (
                                      <option key={run.id} value={run.id} className={styles.customSelectOption}>
                                        {formatDateTime(run.created_at)} ({run.repo_branch}) - {statusLabel(run)}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                        {selectedJob ? <Badge variant="status" type={statusLabel(selectedJob)}>{statusLabel(selectedJob)}</Badge> : <ShieldCheck size={18} className={styles.metricIcon} />}
                      </div>
                      <p className={mobile.panelCopy}>
                        {selectedJob
                          ? `Reviewing branch ${selectedJob.repo_branch}. Status and findings below reflect the selected audit only.`
                          : "Pick an audit to see its findings, report state, and current posture in one place."}
                      </p>
                      <div className={mobile.overviewStats}>
                        <div className={mobile.overviewStat}>
                          <span>Posture</span>
                          <strong>{posture}</strong>
                        </div>
                        <div className={mobile.overviewStat}>
                          <span>Risk score</span>
                          <strong>{riskScore === null ? "—" : `${riskScore}/100`}</strong>
                        </div>
                        <div className={mobile.overviewStat}>
                          <span>Critical</span>
                          <strong>{severityCounts.critical}</strong>
                        </div>
                      </div>
                      <div className={mobile.severityStrip} aria-label="Finding severity breakdown">
                        <span>Critical {severityCounts.critical}</span>
                        <span>High {severityCounts.high}</span>
                        <span>Medium {severityCounts.medium}</span>
                        <span>Low {severityCounts.low}</span>
                      </div>
                      <div className={mobile.quickActionGrid}>
                        <Button type="button" variant="primary" onClick={() => setActiveSection("audits")}><PlusCircle size={14} />New audit</Button>
                        <Button type="button" variant="ghost" disabled={!selectedJob || submitting} onClick={() => selectedJob && handleLaunchScan(selectedJob.repo_url, selectedJob.repo_branch)}><Play size={14} />Re-run</Button>
                        <Button type="button" variant="ghost" onClick={() => setActiveSection("findings")}><Search size={14} />Findings</Button>
                        <Button type="button" variant="ghost" disabled={!latestReportJob} onClick={() => latestReportJob && openReport(latestReportJob.id)}><Download size={14} />Report</Button>
                      </div>
                    </Card>
                  </motion.div>
                  <motion.div variants={scaleUp}>
                    <Card variant="surface" className={styles.panel}>
                      <div className={styles.panelHeader}>
                        <div>
                          <div className={styles.sectionKicker}>Latest audit</div>
                          <h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit yet"}</h2>
                        </div>
                        {selectedJob && <Badge variant="status" type={statusLabel(selectedJob)}>{statusLabel(selectedJob)}</Badge>}
                      </div>
                      <div className={mobile.auditMetaList}>
                        <div className={mobile.auditMetaRow}>
                          <span>Branch</span>
                          <strong>{selectedJob?.repo_branch || "—"}</strong>
                        </div>
                        <div className={mobile.auditMetaRow}>
                          <span>Created</span>
                          <strong>{selectedJob ? formatDateTime(selectedJob.created_at) : "—"}</strong>
                        </div>
                        <div className={mobile.auditMetaRow}>
                          <span>Report</span>
                          <strong>{selectedJob?.report_pdf_url ? "Available" : "Pending"}</strong>
                        </div>
                      </div>
                    </Card>
                  </motion.div>
                </div>
                <div className={mobile.homeSidebar}>
                  <motion.div variants={scaleUp}>
                    <Card variant="surface" className={styles.panel}>
                      <div className={styles.panelHeader}>
                        <div>
                          <div className={styles.sectionKicker}>System</div>
                          <h2>{systemStatus?.api || "Checking"}</h2>
                        </div>
                        <Button variant="ghost" size="sm" onClick={fetchSystemStatus} disabled={loadingSystem}><RefreshCw className={loadingSystem ? styles.spin : ""} size={12} />Refresh</Button>
                      </div>
                      {systemError && <div className={styles.noticeError}>{systemError}</div>}
                      <div className={mobile.statusStrip}>
                        <span><Globe size={13} /> API {systemStatus?.api || "checking"}</span>
                        <span><Database size={13} /> DB {systemStatus?.database || "checking"}</span>
                        <span><HardDrive size={13} /> {systemStatus?.sandbox_mode || "sandbox"}</span>
                      </div>
                    </Card>
                  </motion.div>
                  <motion.div variants={scaleUp}>
                    <Card variant="surface" className={styles.panel}>
                      <div className={styles.panelHeader}>
                        <div>
                          <div className={styles.sectionKicker}>Recent activity</div>
                          <h2>Latest runs</h2>
                        </div>
                      </div>
                      <div className={mobile.timelineList}>
                        {recentJobs.map((job) => (
                          <button
                            key={job.id}
                            type="button"
                            className={mobile.timelineItem}
                            onClick={() => {
                              setSelectedJobId(job.id);
                              setActiveSection("audits");
                              fetchJobDetail(job.id);
                            }}
                          >
                            <span>{formatDateTime(job.created_at)}</span>
                            <strong>{shortRepoName(job.repo_url)}</strong>
                            <Badge variant="status" type={statusLabel(job)}>{statusLabel(job)}</Badge>
                          </button>
                        ))}
                        {jobs.length === 0 && <div className={styles.emptyState}>No audit activity is available yet.</div>}
                      </div>
                    </Card>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          )}

          {activeSection === "audits" && (
            <motion.div key="audits" initial="hidden" animate="visible" exit="exit" variants={staggerContainer}>
               <div className={styles.workGrid}><motion.div variants={scaleUp}><AuditForm onSubmit={handleLaunchScan} onBulkSubmit={handleLaunchBulkScan} submitting={submitting} submitError={submitError} token={token} /></motion.div><motion.div variants={scaleUp}><JobList jobs={jobs} selectedJobId={selectedJobId} loadingJobs={loadingJobs} onRefresh={fetchJobs} onJobSelect={(jobId) => { setSelectedJobId(jobId); fetchJobDetail(jobId); }} /></motion.div></div>
              <div className={styles.detailGrid}><motion.div variants={scaleUp}><PipelineViz job={selectedJob} onOpenReport={openReport} onCancel={cancelScan} reportError={reportError} /></motion.div><motion.div variants={scaleUp}><Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Status</div><h2>{selectedJob ? statusLabel(selectedJob) : "No audit selected"}</h2></div><Badge variant="status" type={streamActive ? "running" : selectedJob ? statusLabel(selectedJob) : "queued"}>{streamActive ? "live logs" : selectedJob ? statusLabel(selectedJob) : "idle"}</Badge></div><p className={mobile.panelCopy}>{selectedJob ? "The selected audit controls the summary, report action, and log panel below." : "Choose an audit from the list to inspect its saved state."}</p></Card></motion.div></div>
              <motion.div variants={scaleUp}><LogStream logs={logs} streamActive={streamActive} hasSelection={Boolean(selectedJobId)} /></motion.div>
            </motion.div>
          )}

          {activeSection === "findings" && (
            <motion.div key="findings" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <div className={mobile.findingsHeroGrid}>
                <Card variant="surface" className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <div>
                      <div className={styles.sectionKicker}>Selected Audit</div>
                      <h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit selected"}</h2>
                    </div>
                    {selectedJob && <Badge variant="status" type={statusLabel(selectedJob)}>{statusLabel(selectedJob)}</Badge>}
                  </div>
                  <p className={mobile.panelCopy}>
                    {selectedJob 
                      ? `Showing findings returned for branch ${selectedJob.repo_branch}. Select another audit below or from the Audits tab to inspect its details.` 
                      : "Start or select an audit to review evidence-backed findings."}
                  </p>
                  {uniqueRepos.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "14px" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px", flexGrow: 1, minWidth: "200px" }}>
                        <label style={{ fontSize: "11px", color: "var(--muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>Repository</label>
                        <select
                          value={currentRepoUrl || ""}
                          onChange={(e) => handleRepoChange(e.target.value)}
                          className={styles.customSelect}
                        >
                          {uniqueRepos.map((repo) => (
                            <option key={repo.url} value={repo.url} className={styles.customSelectOption}>
                              {repo.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px", flexGrow: 1, minWidth: "200px" }}>
                        <label style={{ fontSize: "11px", color: "var(--muted)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>Run History</label>
                        <select
                          value={selectedJobId || ""}
                          onChange={(e) => {
                            const jobId = e.target.value;
                            setSelectedJobId(jobId);
                            fetchJobDetail(jobId);
                          }}
                          className={styles.customSelect}
                        >
                          {repoRuns.map((run) => (
                            <option key={run.id} value={run.id} className={styles.customSelectOption}>
                              {formatDateTime(run.created_at)} ({run.repo_branch}) - {statusLabel(run)}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}
                </Card>
                <Card variant="surface" className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <div>
                      <div className={styles.sectionKicker}>Critical / High</div>
                      <h2>{criticalFindings + highFindings}</h2>
                    </div>
                    <AlertTriangle size={18} className={styles.metricIcon} />
                  </div>
                  <p className={mobile.panelCopy}>Severity labels are shown in text and color; color is never the only signal.</p>
                </Card>
              </div>
              <FindingsList findings={findings} loading={loadingDetail} />
            </motion.div>
          )}

          {activeSection === "reports" && (
            <motion.div key="reports" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Reports</div><h2>Audit reports</h2></div><Button variant="ghost" size="sm" onClick={fetchJobs} disabled={!token || loadingJobs}><RefreshCw className={loadingJobs ? styles.spin : ""} size={12} />Refresh</Button></div><div className={styles.reportList}>{reportError && <div className={styles.noticeError}>{reportError}</div>}{!token ? <div className={styles.emptyState}>Connect a workspace to view reports.</div> : reportJobs.length === 0 ? <div className={styles.emptyState}>No audit reports are available yet. Start an authorized audit to generate your first report.</div> : reportJobs.map((job) => <motion.article whileHover={{ scale: 1.01 }} className={styles.reportRow} key={job.id}><div><Badge variant="status" type={statusLabel(job)}>{statusLabel(job)}</Badge><h3>{shortRepoName(job.repo_url)}</h3><p>Branch {job.repo_branch} / finished {formatDateTime(job.finished_at)}</p></div>{job.report_pdf_url ? <Button variant="ghost" size="sm" onClick={() => openReport(job.id)}><FileText size={14} />Open report</Button> : <span className={styles.reportMissing}>No PDF artifact</span>}</motion.article>)}</div></Card>
            </motion.div>
          )}

          {activeSection === "settings" && (
            <motion.div key="settings" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Settings</div><h2>Workspace settings</h2></div><Button variant="ghost" size="sm" onClick={fetchSystemStatus} disabled={loadingSystem}><RefreshCw className={loadingSystem ? styles.spin : ""} size={12} />Refresh</Button></div>{systemError && <div className={styles.noticeError}>{systemError}</div>}<div className={styles.settingsGrid}><StatusCard label="API" value={systemStatus?.api || "checking"} tone={systemStatus?.api === "online" ? "good" : "warn"} icon={<Globe size={14} />} /><StatusCard label="Database" value={systemStatus?.database || "checking"} tone={systemStatus?.database === "connected" ? "good" : "warn"} icon={<Database size={14} />} /><StatusCard label="Sandbox" value={systemStatus?.sandbox_mode === "docker" ? "Docker/Kali" : "Simulation"} tone="warn" icon={<HardDrive size={14} />} /><StatusCard label="Workspace" value={username || "Not connected"} tone={username ? "good" : "warn"} icon={<Fingerprint size={14} />} /></div><div className={styles.integrationList}>{Object.entries(systemStatus?.integrations || {}).map(([name, enabled]) => <motion.div whileHover={{ x: 2 }} className={styles.integrationRow} key={name}><span>{name.replaceAll("_", " ")}</span><strong className={enabled ? styles.integrationOn : styles.integrationOff}>{enabled ? "configured" : "not configured"}</strong></motion.div>)}<div className={styles.integrationRow}><span>PWA offline policy</span><strong className={styles.integrationOn}>private API data not cached</strong></div><div className={styles.integrationRow}><span>Install help</span><strong className={styles.integrationOn}>use browser install prompt when available</strong></div>{!systemStatus && !systemError && <div className={styles.emptyState}>System status has not loaded yet.</div>}</div><div className={mobile.settingsActions}><Button type="button" variant="danger" onClick={signOut}><LogOut size={14} />Logout</Button></div></Card>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.section>
    </main>
  );
}

function StatusCard({ label, value, tone, icon }: { label: string; value: string; tone: "good" | "warn"; icon?: React.ReactNode }) {
  const cardClass = [styles.statusCard, tone === "good" ? styles.statusCardGood : styles.statusCardWarn].join(" ");
  return <div className={cardClass}><div className={styles.statusCardHeader}><span>{label}</span>{icon}</div><strong>{value}</strong></div>;
}
