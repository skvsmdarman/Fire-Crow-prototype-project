"use client";

import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
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
  home: "Home",
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

function pipelineIndex(status: JobStatus, logs: LogLine[]): number {
  if (status === "queued") return 0;
  if (status === "completed" || status === "partial") return 9;
  if (status === "failed" || status === "cancelled") return -1;

  let index = 1;
  for (const log of logs) {
    const message = log.message.toLowerCase();
    if (message.includes("static") || message.includes("sast")) index = Math.max(index, 1);
    if (message.includes("sandbox") || message.includes("kali")) index = Math.max(index, 2);
    if (message.includes("port") || message.includes("network")) index = Math.max(index, 3);
    if (message.includes("validation") || message.includes("scanner")) index = Math.max(index, 4);
    if (message.includes("proof") || message.includes("evidence")) index = Math.max(index, 5);
    if (message.includes("cvss") || message.includes("scoring")) index = Math.max(index, 6);
    if (message.includes("report") || message.includes("pdf")) index = Math.max(index, 7);
    if (message.includes("google") || message.includes("gmail") || message.includes("pr risk")) index = Math.max(index, 8);
    if (message.includes("cleanup") || message.includes("deprovision")) index = Math.max(index, 9);
  }
  return index;
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
    localStorage.removeItem("fc_token");
    localStorage.removeItem("fc_username");
    localStorage.removeItem("fc_user_id");
    router.push("/signin");
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
        const response = await fetch(`${API_BASE_URL}/auth/me`, { headers: { Authorization: `Bearer ${savedToken}` } });
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
        localStorage.removeItem("fc_token");
        localStorage.removeItem("fc_username");
        localStorage.removeItem("fc_user_id");
        router.replace("/signin");
      }
    };
    void validateToken();
  }, [router]);

  useEffect(() => { if (token) fetchJobs(); }, [fetchJobs, token]);
  useEffect(() => { if (token) fetchSystemStatus(); }, [fetchSystemStatus, token]);
  useEffect(() => { if (selectedJobId && token) fetchJobDetail(selectedJobId); }, [fetchJobDetail, selectedJobId, token]);
  useEffect(() => {
    if (!selectedJob || !token || (selectedJob.status !== "queued" && selectedJob.status !== "running")) return;
    const interval = window.setInterval(() => {
      fetchJobs();
      fetchJobDetail(selectedJob.id);
    }, 3500);
    return () => window.clearInterval(interval);
  }, [fetchJobDetail, fetchJobs, selectedJob, token]);

  const activeStep = selectedJob ? pipelineIndex(selectedJob.status, logs) : 0;
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
            <div className={styles.sectionKicker}>Fire Crow mobile command center</div>
            <h1>{SECTION_TITLES[activeSection]}</h1>
          </div>
          <div className={styles.workspaceSession}>
            <User size={13} style={{ color: "var(--fire)", marginRight: 2 }} />
            <span>{username}</span>
            <Button variant="ghost" size="sm" onClick={signOut} style={{ minHeight: "32px", fontSize: "11px", padding: "0 8px" }}><LogOut size={12} />Sign out</Button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          {activeSection === "home" && (
            <motion.div key="home" initial="hidden" animate="visible" exit="exit" variants={staggerContainer}>
              <motion.div variants={fadeInUp}><MetricsRow activeAudits={activeJobs} totalJobs={jobs.length} criticalFindings={criticalFindings} latestReport={latestReport} /></motion.div>
              <div className={mobile.homeGrid}>
                <motion.div variants={scaleUp}>
                  <Card variant="surface" className={`${styles.panel} ${mobile.postureCard}`}>
                    <div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Overall Security Posture</div><h2>{posture}</h2></div><ShieldCheck size={22} className={styles.metricIcon} /></div>
                    <p className={mobile.panelCopy}>{riskScore === null ? "Start an authorized audit to generate a real posture score from backend findings." : "Posture is calculated from the selected audit findings currently returned by the backend."}</p>
                    <div className={mobile.severityStrip} aria-label="Finding severity breakdown"><span>Critical {severityCounts.critical}</span><span>High {severityCounts.high}</span><span>Medium {severityCounts.medium}</span><span>Low {severityCounts.low}</span></div>
                  </Card>
                </motion.div>
                <motion.div variants={scaleUp}>
                  <Card variant="surface" className={`${styles.panel} ${mobile.riskScoreCard}`}>
                    <div className={mobile.scoreRing} aria-label={riskScore === null ? "Risk score unavailable" : `Risk score ${riskScore} out of 100`}><strong>{riskScore === null ? "—" : riskScore}</strong><span>{riskScore === null ? "No score" : "Risk"}</span></div>
                    <div><div className={styles.sectionKicker}>Risk Score</div><h2>{riskScore === null ? "No audit selected" : `${riskScore}/100`}</h2><p className={mobile.panelCopy}>No score is invented when findings are unavailable.</p></div>
                  </Card>
                </motion.div>
                <motion.div variants={scaleUp}>
                  <Card variant="surface" className={styles.panel}>
                    <div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Last Audit</div><h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit yet"}</h2></div>{selectedJob && <Badge variant="status" type={statusLabel(selectedJob)}>{statusLabel(selectedJob)}</Badge>}</div>
                    <p className={mobile.panelCopy}>{selectedJob ? `Branch ${selectedJob.repo_branch} / created ${formatDateTime(selectedJob.created_at)}` : "No audit records are available yet. Start an authorized audit to generate the first run."}</p>
                  </Card>
                </motion.div>
                <motion.div variants={scaleUp}>
                  <Card variant="surface" className={styles.panel}>
                    <div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Quick Actions</div><h2>Move the review forward</h2></div></div>
                    <div className={mobile.quickActionGrid}>
                      <Button type="button" variant="primary" onClick={() => setActiveSection("audits")}><PlusCircle size={14} />New audit</Button>
                      <Button type="button" variant="ghost" disabled={!selectedJob || submitting} onClick={() => selectedJob && handleLaunchScan(selectedJob.repo_url, selectedJob.repo_branch)}><Play size={14} />Re-run last</Button>
                      <Button type="button" variant="ghost" onClick={() => setActiveSection("findings")}><Search size={14} />Critical findings</Button>
                      <Button type="button" variant="ghost" disabled={!latestReportJob} onClick={() => latestReportJob && openReport(latestReportJob.id)}><Download size={14} />Export report</Button>
                    </div>
                  </Card>
                </motion.div>
                <motion.div variants={scaleUp}>
                  <Card variant="surface" className={styles.panel}>
                    <div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Activity Timeline</div><h2>Recent audit activity</h2></div></div>
                    <div className={mobile.timelineList}>{jobs.slice(0, 4).map((job) => <button key={job.id} type="button" className={mobile.timelineItem} onClick={() => { setSelectedJobId(job.id); setActiveSection("audits"); fetchJobDetail(job.id); }}><span>{formatDateTime(job.created_at)}</span><strong>{shortRepoName(job.repo_url)}</strong><Badge variant="status" type={statusLabel(job)}>{statusLabel(job)}</Badge></button>)}{jobs.length === 0 && <div className={styles.emptyState}>No audit activity is available yet.</div>}</div>
                  </Card>
                </motion.div>
                <motion.div variants={scaleUp}>
                  <Card variant="surface" className={styles.panel}>
                    <div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Backend/API Status</div><h2>{systemStatus?.api || "Checking"}</h2></div><Button variant="ghost" size="sm" onClick={fetchSystemStatus} disabled={loadingSystem}><RefreshCw className={loadingSystem ? styles.spin : ""} size={12} />Refresh</Button></div>
                    {systemError && <div className={styles.noticeError}>{systemError}</div>}
                    <div className={mobile.statusStrip}><span><Globe size={13} /> API {systemStatus?.api || "checking"}</span><span><Database size={13} /> DB {systemStatus?.database || "checking"}</span><span><HardDrive size={13} /> {systemStatus?.sandbox_mode || "sandbox"}</span></div>
                  </Card>
                </motion.div>
              </div>
            </motion.div>
          )}

          {activeSection === "audits" && (
            <motion.div key="audits" initial="hidden" animate="visible" exit="exit" variants={staggerContainer}>
              <div className={styles.workGrid}><motion.div variants={scaleUp}><AuditForm onSubmit={handleLaunchScan} submitting={submitting} submitError={submitError} /></motion.div><motion.div variants={scaleUp}><JobList jobs={jobs} selectedJobId={selectedJobId} loadingJobs={loadingJobs} onRefresh={fetchJobs} onJobSelect={(jobId) => { setSelectedJobId(jobId); fetchJobDetail(jobId); startLogStream(jobId); }} /></motion.div></div>
              <div className={styles.detailGrid}><motion.div variants={scaleUp}><PipelineViz job={selectedJob} activeStep={activeStep} onOpenReport={openReport} onCancel={cancelScan} reportError={reportError} /></motion.div><motion.div variants={scaleUp}><Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Running Screen</div><h2>{selectedJob ? statusLabel(selectedJob) : "No active audit"}</h2></div><Activity size={18} className={streamActive ? styles.spin : styles.metricIcon} /></div><p className={mobile.panelCopy}>Fire Crow maps backend status to pending, running, completed, failed, cancelled, or partial states without inventing precise percentages.</p></Card></motion.div></div>
              <motion.div variants={scaleUp}><LogStream logs={logs} streamActive={streamActive} /></motion.div>
            </motion.div>
          )}

          {activeSection === "findings" && (
            <motion.div key="findings" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <div className={mobile.findingsHeroGrid}><Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Selected Audit</div><h2>{selectedJob ? shortRepoName(selectedJob.repo_url) : "No audit selected"}</h2></div>{selectedJob && <Badge variant="status" type={statusLabel(selectedJob)}>{statusLabel(selectedJob)}</Badge>}</div><p className={mobile.panelCopy}>{selectedJob ? `Showing findings returned for branch ${selectedJob.repo_branch}. Select another audit from the Audits tab to inspect its details.` : "Start or select an audit to review evidence-backed findings."}</p></Card><Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Critical / High</div><h2>{criticalFindings + highFindings}</h2></div><AlertTriangle size={18} className={styles.metricIcon} /></div><p className={mobile.panelCopy}>Severity labels are shown in text and color; color is never the only signal.</p></Card></div>
              <FindingsList findings={findings} loading={loadingDetail} />
            </motion.div>
          )}

          {activeSection === "reports" && (
            <motion.div key="reports" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Reports</div><h2>Released audit artifacts</h2></div><Button variant="ghost" size="sm" onClick={fetchJobs} disabled={!token || loadingJobs}><RefreshCw className={loadingJobs ? styles.spin : ""} size={12} />Refresh</Button></div><div className={styles.reportList}>{reportError && <div className={styles.noticeError}>{reportError}</div>}{!token ? <div className={styles.emptyState}>Connect a workspace to view reports.</div> : reportJobs.length === 0 ? <div className={styles.emptyState}>No audit reports are available yet. Start an authorized audit to generate your first report.</div> : reportJobs.map((job) => <motion.article whileHover={{ scale: 1.01 }} className={styles.reportRow} key={job.id}><div><Badge variant="status" type={statusLabel(job)}>{statusLabel(job)}</Badge><h3>{shortRepoName(job.repo_url)}</h3><p>Branch {job.repo_branch} / finished {formatDateTime(job.finished_at)}</p></div>{job.report_pdf_url ? <Button variant="ghost" size="sm" onClick={() => openReport(job.id)}><FileText size={14} />Open report</Button> : <span className={styles.reportMissing}>No PDF artifact</span>}</motion.article>)}</div></Card>
            </motion.div>
          )}

          {activeSection === "settings" && (
            <motion.div key="settings" initial="hidden" animate="visible" exit="exit" variants={tabTransition} className={styles.sectionBody}>
              <Card variant="surface" className={styles.panel}><div className={styles.panelHeader}><div><div className={styles.sectionKicker}>Settings</div><h2>Account, security, and PWA status</h2></div><Button variant="ghost" size="sm" onClick={fetchSystemStatus} disabled={loadingSystem}><RefreshCw className={loadingSystem ? styles.spin : ""} size={12} />Refresh</Button></div>{systemError && <div className={styles.noticeError}>{systemError}</div>}<div className={styles.settingsGrid}><StatusCard label="API" value={systemStatus?.api || "checking"} tone={systemStatus?.api === "online" ? "good" : "warn"} icon={<Globe size={14} />} /><StatusCard label="Database" value={systemStatus?.database || "checking"} tone={systemStatus?.database === "connected" ? "good" : "warn"} icon={<Database size={14} />} /><StatusCard label="Sandbox" value={systemStatus?.sandbox_mode === "docker" ? "Docker/Kali" : "Simulation"} tone="warn" icon={<HardDrive size={14} />} /><StatusCard label="Workspace" value={username || "Not connected"} tone={username ? "good" : "warn"} icon={<Fingerprint size={14} />} /></div><div className={styles.integrationList}>{Object.entries(systemStatus?.integrations || {}).map(([name, enabled]) => <motion.div whileHover={{ x: 2 }} className={styles.integrationRow} key={name}><span>{name.replaceAll("_", " ")}</span><strong className={enabled ? styles.integrationOn : styles.integrationOff}>{enabled ? "configured" : "not configured"}</strong></motion.div>)}<div className={styles.integrationRow}><span>PWA offline policy</span><strong className={styles.integrationOn}>private API data not cached</strong></div><div className={styles.integrationRow}><span>Install help</span><strong className={styles.integrationOn}>use browser install prompt when available</strong></div>{!systemStatus && !systemError && <div className={styles.emptyState}>System status has not loaded yet.</div>}</div><div className={mobile.settingsActions}><Button type="button" variant="danger" onClick={signOut}><LogOut size={14} />Logout</Button></div></Card>
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
