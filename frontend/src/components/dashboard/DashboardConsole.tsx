"use client";

import Link from "next/link";
import { startTransition, useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { clearSession, getSessionIdentity } from "../../lib/auth-session";
import { buildApiUrl } from "../../lib/base-url";
import { enablePushNotifications } from "../../lib/push";
import { ApiError, request } from "../../lib/request";
import { formatRelativeDate, formatRepoName, scoreLabel, severityRank } from "../../lib/format";
import {
  AuditInsightResponse,
  AuthUser,
  ChatResponse,
  Finding,
  Job,
  JobDetailResponse,
  LeaderboardEntry,
  SubmitAuditRequest,
  SystemStatus,
} from "../../lib/types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { SiteHeader } from "../SiteChrome";

type DashboardTab = "operations" | "findings" | "reports" | "signals" | "settings";
type StreamEntry = { event: string; text: string; at: string };
type ChatMessage = { role: "user" | "assistant"; text: string };

const DASHBOARD_TABS: Array<{ id: DashboardTab; label: string }> = [
  { id: "operations", label: "Operations" },
  { id: "findings", label: "Findings" },
  { id: "reports", label: "Reports" },
  { id: "signals", label: "Signals" },
  { id: "settings", label: "Settings" },
];

function parseEventBlock(block: string): { event: string; data: string } | null {
  const lines = block.split(/\r?\n/).filter(Boolean);
  if (!lines.length) {
    return null;
  }

  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  return { event, data: dataLines.join("\n") };
}

async function consumeAuditStream(
  jobId: string,
  onEvent: (entry: StreamEntry) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(buildApiUrl(`/audit/${jobId}/stream`), {
    credentials: "include",
    signal,
  });
  if (!response.ok || !response.body) {
    throw new ApiError(`Stream unavailable (${response.status})`, response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const parsed = parseEventBlock(block);
      if (!parsed) {
        continue;
      }
      let text = parsed.data;
      try {
        const json = JSON.parse(parsed.data);
        text = typeof json === "string" ? json : JSON.stringify(json);
      } catch {
        // Keep plain text payloads.
      }

      onEvent({
        event: parsed.event,
        text,
        at: new Date().toISOString(),
      });
    }
  }
}

export function DashboardConsole() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialWorkspace = searchParams.get("workspace") ?? getSessionIdentity().workspace ?? "workspace";
  const requestedJobId = searchParams.get("jobId") ?? searchParams.get("job_id");

  const [tab, setTab] = useState<DashboardTab>("operations");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(requestedJobId);
  const [jobDetail, setJobDetail] = useState<JobDetailResponse | null>(null);
  const [insight, setInsight] = useState<AuditInsightResponse | null>(null);
  const [graph, setGraph] = useState<unknown>(null);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [stream, setStream] = useState<StreamEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [pushMessage, setPushMessage] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "When the chat assistant feature flag is enabled, ask for a summary of evidence or next-response guidance for the selected audit.",
    },
  ]);
  const [auditForm, setAuditForm] = useState({
    repo_url: "",
    repo_branch: "main",
    authorization_scope: "authorized_representative",
  });
  const [findingSearch, setFindingSearch] = useState("");

  const deferredSearch = useDeferredValue(findingSearch.trim().toLowerCase());
  const selectedJob = jobDetail?.job ?? jobs.find((job) => job.id === selectedJobId) ?? null;
  const findings = useMemo(() => {
    const source = jobDetail?.findings ?? [];
    return [...source]
      .filter((finding) => {
        if (!deferredSearch) {
          return true;
        }
        return [finding.title, finding.description, finding.agent_source, finding.severity]
          .join(" ")
          .toLowerCase()
          .includes(deferredSearch);
      })
      .sort((left, right) => severityRank(right.severity) - severityRank(left.severity));
  }, [deferredSearch, jobDetail?.findings]);

  const fetchDashboard = useCallback(async (preserveSelection = true) => {
    try {
      const [user, status, nextJobs, nextLeaderboard] = await Promise.all([
        request<AuthUser>("/auth/me"),
        request<SystemStatus>("/system/status"),
        request<Job[]>("/audit/jobs"),
        request<LeaderboardEntry[]>("/leaderboard").catch(() => []),
      ]);

      setAuthUser(user);
      setSystemStatus(status);
      setJobs(nextJobs);
      setLeaderboard(nextLeaderboard);
      setReconnecting(false);

      const fallbackJobId = nextJobs[0]?.id ?? null;
      if (!preserveSelection || !selectedJobId || !nextJobs.some((job) => job.id === selectedJobId)) {
        startTransition(() => {
          setSelectedJobId(fallbackJobId);
        });
      }
    } catch (error) {
      if (error instanceof ApiError && error.status && error.status < 500) {
        throw error;
      }
      setReconnecting(true);
    }
  }, [selectedJobId]);

  const fetchDetail = useCallback(async (jobId: string) => {
    try {
      const detail = await request<JobDetailResponse>(`/audit/job/${jobId}`);
      setJobDetail(detail);
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 404)) {
        setFormError(error instanceof ApiError ? error.message : "Failed to load audit detail.");
      }
    }
  }, []);

  const fetchSignals = useCallback(async (jobId: string) => {
    try {
      const nextInsight = await request<AuditInsightResponse>(`/audit/job/${jobId}/insight`);
      setInsight(nextInsight);
    } catch {
      setInsight(null);
    }

    try {
      const nextGraph = await request<unknown>(`/audit/job/${jobId}/graph`);
      setGraph(nextGraph);
      setGraphError(null);
    } catch (error) {
      setGraph(null);
      setGraphError(error instanceof ApiError ? error.message : "Attack graph unavailable.");
    }
  }, []);

  useEffect(() => {
    if (!requestedJobId) {
      return;
    }
    setSelectedJobId(requestedJobId);
  }, [requestedJobId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    void fetchDashboard(false)
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchDashboard]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setRefreshing(true);
      void fetchDashboard(true).finally(() => setRefreshing(false));
    }, 15000);

    return () => window.clearInterval(timer);
  }, [fetchDashboard]);

  useEffect(() => {
    if (!selectedJobId) {
      setJobDetail(null);
      setInsight(null);
      setGraph(null);
      setGraphError(null);
      setStream([]);
      return;
    }

    setFormError(null);
    setJobDetail(null);
    setStream([]);
    void fetchDetail(selectedJobId);
    void fetchSignals(selectedJobId);
  }, [fetchDetail, fetchSignals, selectedJobId]);

  useEffect(() => {
    if (!selectedJobId || !selectedJob || !["queued", "running"].includes(selectedJob.status)) {
      return;
    }

    const controller = new AbortController();
    setStream([]);

    void consumeAuditStream(
      selectedJobId,
      (entry) => {
        setStream((current) => [...current.slice(-59), entry]);
        if (entry.event === "complete") {
          void fetchDashboard(true);
          void fetchDetail(selectedJobId);
        }
      },
      controller.signal,
    ).catch((error) => {
      if (!controller.signal.aborted) {
        setStream((current) => [
          ...current,
          {
            event: "error",
            text: error instanceof Error ? error.message : "Stream interrupted.",
            at: new Date().toISOString(),
          },
        ]);
      }
    });

    return () => controller.abort();
  }, [fetchDashboard, fetchDetail, selectedJob, selectedJobId]);

  async function handleSubmit() {
    setSubmitting(true);
    setFormError(null);

    try {
      const payload: SubmitAuditRequest = {
        repo_url: auditForm.repo_url.trim(),
        repo_branch: auditForm.repo_branch.trim() || "main",
        attestation_accepted: true,
        authorization_scope: auditForm.authorization_scope.trim() || "authorized_representative",
      };

      const response = await request<Job>("/audit/submit", {
        method: "POST",
        body: payload,
      });

      setJobs((current) => [response, ...current]);
      setSelectedJobId(response.id);
      setTab("operations");
      await fetchDashboard(true);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Audit launch failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel(jobId: string) {
    try {
      await request(`/audit/job/${jobId}`, { method: "DELETE" });
      await fetchDashboard(true);
      if (selectedJobId === jobId) {
        await fetchDetail(jobId);
      }
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Cancellation failed.");
    }
  }

  async function handleLogout() {
    try {
      await request("/auth/logout", { method: "POST" });
    } catch {
      // Clearing local session is still correct if backend logout is unavailable.
    } finally {
      clearSession();
      router.replace("/signin");
    }
  }

  async function handlePushEnable() {
    try {
      setPushMessage(await enablePushNotifications());
    } catch (error) {
      setPushMessage(error instanceof Error ? error.message : "Push registration failed.");
    }
  }

  async function handleChatSubmit() {
    if (!selectedJobId || !chatInput.trim()) {
      return;
    }

    const message = chatInput.trim();
    setChatMessages((current) => [...current, { role: "user", text: message }]);
    setChatInput("");
    setChatBusy(true);

    try {
      const response = await request<ChatResponse>("/chat/ask", {
        method: "POST",
        body: { job_id: selectedJobId, message },
      });
      setChatMessages((current) => [
        ...current,
        { role: "assistant", text: response.answer ?? response.response ?? "No assistant response was returned." },
      ]);
    } catch (error) {
      setChatMessages((current) => [
        ...current,
        { role: "assistant", text: error instanceof ApiError ? error.message : "Chat assistant request failed." },
      ]);
    } finally {
      setChatBusy(false);
    }
  }

  function openReport(jobId: string) {
    window.open(buildApiUrl(`/audit/job/${jobId}/report`), "_blank", "noopener,noreferrer");
  }

  const completedJobs = jobs.filter((job) => ["completed", "partial"].includes(job.status));
  const workspaceName = authUser?.username ?? initialWorkspace;

  return (
    <div className="fc-page">
      <SiteHeader ctaHref="/" ctaLabel="Landing Page" />
      <main className="fc-shell fc-dashboard-shell">
        <div className="fc-dashboard-grid">
          <Card className="fc-sidebar">
            <div>
              <div className="fc-kicker">Workspace</div>
              <h1 className="fc-panel-title" style={{ marginTop: 10 }}>
                {workspaceName}
              </h1>
              <div className="fc-copy" style={{ marginTop: 10 }}>
                Authenticated operations console backed by live session cookies and policy-aware scan submission.
              </div>
            </div>

            <div className="fc-sidebar-nav">
              {DASHBOARD_TABS.map((item) => (
                <button
                  key={item.id}
                  className="fc-sidebar-tab"
                  data-active={tab === item.id}
                  onClick={() => setTab(item.id)}
                  type="button"
                >
                  <span>{item.label}</span>
                  <span className="fc-muted">{item.id === "reports" ? completedJobs.length : item.id === "findings" ? findings.length : null}</span>
                </button>
              ))}
            </div>

            <Card className="fc-panel">
              <div className="fc-kicker">System</div>
              <div className="fc-chip-row" style={{ marginTop: 12 }}>
                <Badge tone={systemStatus?.api === "online" ? "success" : "warning"}>{systemStatus?.api ?? "Loading API"}</Badge>
                <Badge tone={systemStatus?.database === "connected" ? "success" : "critical"}>{systemStatus?.database ?? "DB"}</Badge>
                {reconnecting ? <Badge tone="warning">Reconnecting</Badge> : null}
                {refreshing ? <Badge tone="info">Refreshing</Badge> : null}
              </div>
            </Card>

            <div className="fc-chip-row">
              <Button variant="secondary" onClick={handlePushEnable}>
                Enable push
              </Button>
              <Button variant="ghost" onClick={handleLogout}>
                Sign out
              </Button>
            </div>
          </Card>

          <div className="fc-dashboard-main">
            {loading ? (
              <Card className="fc-panel">
                <div className="fc-panel-title">Loading dashboard...</div>
              </Card>
            ) : null}

            {pushMessage ? <div className="fc-form-success">{pushMessage}</div> : null}
            {formError ? <div className="fc-form-error">{formError}</div> : null}
            {reconnecting ? (
              <div className="fc-form-error">The dashboard is in read-only reconnect mode. Local session state is preserved until connectivity returns.</div>
            ) : null}

            <OverviewPanel authUser={authUser} selectedJob={selectedJob} systemStatus={systemStatus} />

            {tab === "operations" ? (
              <>
                <LaunchPanel
                  auditForm={auditForm}
                  onChange={setAuditForm}
                  onSubmit={handleSubmit}
                  submitting={submitting}
                />
                <JobsPanel
                  jobs={jobs}
                  selectedJobId={selectedJobId}
                  onSelect={(jobId) => startTransition(() => setSelectedJobId(jobId))}
                  onCancel={handleCancel}
                  onOpenReport={openReport}
                />
                <StreamPanel selectedJob={selectedJob} stream={stream} />
              </>
            ) : null}

            {tab === "findings" ? (
              <FindingsPanel
                findings={findings}
                selectedJob={selectedJob}
                search={findingSearch}
                onSearch={setFindingSearch}
              />
            ) : null}

            {tab === "reports" ? (
              <ReportsPanel jobs={completedJobs} onOpenReport={openReport} />
            ) : null}

            {tab === "signals" ? (
              <>
                <SignalsPanel
                  graph={graph}
                  graphError={graphError}
                  insight={insight}
                  selectedJob={selectedJob}
                />
                <LeaderboardPanel entries={leaderboard} />
                <ChatPanel
                  enabled={Boolean(systemStatus?.llm_features?.chat_assistant)}
                  messages={chatMessages}
                  input={chatInput}
                  onInput={setChatInput}
                  onSubmit={handleChatSubmit}
                  busy={chatBusy}
                  selectedJobId={selectedJobId}
                />
              </>
            ) : null}

            {tab === "settings" ? (
              <SettingsPanel authUser={authUser} systemStatus={systemStatus} onPushEnable={handlePushEnable} />
            ) : null}

            {selectedJobId ? (
              <Card className="fc-panel">
                <div className="fc-panel-head">
                  <div>
                    <div className="fc-kicker">Deep dive</div>
                    <h2 className="fc-panel-title">Audit detail view</h2>
                  </div>
                  <Link className="fc-button fc-button-secondary" href={`/dashboard/audits/default?jobId=${encodeURIComponent(selectedJobId)}`}>
                    Open dedicated audit page
                  </Link>
                </div>
              </Card>
            ) : null}
          </div>
        </div>
      </main>
    </div>
  );
}

function OverviewPanel({
  authUser,
  selectedJob,
  systemStatus,
}: {
  authUser: AuthUser | null;
  selectedJob: Job | null;
  systemStatus: SystemStatus | null;
}) {
  return (
    <div className="fc-grid-3">
      <Card className="fc-panel fc-metric">
        <div className="fc-muted">Current session</div>
        <span className="fc-metric-value">{authUser?.username ?? "Unknown"}</span>
        <div className="fc-copy">Workspace session validated via `/auth/me` and cookie-backed auth.</div>
      </Card>
      <Card className="fc-panel fc-metric">
        <div className="fc-muted">Selected audit</div>
        <span className="fc-metric-value">{selectedJob ? selectedJob.status : "None"}</span>
        <div className="fc-copy">{selectedJob ? formatRepoName(selectedJob.repo_url) : "Choose or launch an audit to inspect live output."}</div>
      </Card>
      <Card className="fc-panel fc-metric">
        <div className="fc-muted">System posture</div>
        <span className="fc-metric-value">{systemStatus?.stats?.findings ?? 0}</span>
        <div className="fc-copy">Findings currently associated with the signed-in workspace.</div>
      </Card>
    </div>
  );
}

function LaunchPanel({
  auditForm,
  onChange,
  onSubmit,
  submitting,
}: {
  auditForm: { repo_url: string; repo_branch: string; authorization_scope: string };
  onChange: (
    next:
      | { repo_url: string; repo_branch: string; authorization_scope: string }
      | ((current: { repo_url: string; repo_branch: string; authorization_scope: string }) => {
          repo_url: string;
          repo_branch: string;
          authorization_scope: string;
        }),
  ) => void;
  onSubmit: () => void;
  submitting: boolean;
}) {
  return (
    <Card className="fc-panel">
      <div className="fc-panel-head">
        <div>
          <div className="fc-kicker">Launch audit</div>
          <h2 className="fc-panel-title">Submit an authorized repository.</h2>
        </div>
        <Badge tone="warning">Attestation enforced</Badge>
      </div>
      <div className="fc-inline-fields">
        <label className="fc-field">
          <span className="fc-field-label">Repository URL</span>
          <Input
            value={auditForm.repo_url}
            onChange={(event) => onChange((current) => ({ ...current, repo_url: event.target.value }))}
            placeholder="https://github.com/owner/repo"
          />
        </label>
        <label className="fc-field">
          <span className="fc-field-label">Branch</span>
          <Input
            value={auditForm.repo_branch}
            onChange={(event) => onChange((current) => ({ ...current, repo_branch: event.target.value }))}
            placeholder="main"
          />
        </label>
      </div>
      <label className="fc-field" style={{ marginTop: 14 }}>
        <span className="fc-field-label">Authorization scope</span>
        <Input
          value={auditForm.authorization_scope}
          onChange={(event) => onChange((current) => ({ ...current, authorization_scope: event.target.value }))}
        />
      </label>
      <div className="fc-chip-row" style={{ marginTop: 16 }}>
        <Button loading={submitting} onClick={onSubmit}>
          Launch audit
        </Button>
      </div>
    </Card>
  );
}

function JobsPanel({
  jobs,
  selectedJobId,
  onSelect,
  onCancel,
  onOpenReport,
}: {
  jobs: Job[];
  selectedJobId: string | null;
  onSelect: (jobId: string) => void;
  onCancel: (jobId: string) => void;
  onOpenReport: (jobId: string) => void;
}) {
  return (
    <Card className="fc-panel">
      <div className="fc-panel-head">
        <div>
          <div className="fc-kicker">Audit queue</div>
          <h2 className="fc-panel-title">Live job list</h2>
        </div>
        <Badge tone="info">{jobs.length} jobs</Badge>
      </div>
      {jobs.length ? (
        <div className="fc-table">
          {jobs.map((job) => (
            <div className="fc-table-row" data-active={selectedJobId === job.id} key={job.id}>
              <div style={{ flex: 1 }}>
                <div className="fc-stack-between">
                  <strong>{formatRepoName(job.repo_url)}</strong>
                  <Badge tone={job.status === "completed" ? "success" : job.status === "failed" ? "critical" : "warning"}>
                    {job.status}
                  </Badge>
                </div>
                <div className="fc-copy" style={{ marginTop: 8 }}>
                  {job.repo_branch} • Created {formatRelativeDate(job.created_at)}
                </div>
                {job.security_score != null ? <div className="fc-muted">Security score {job.security_score} • {scoreLabel(job.security_score)}</div> : null}
              </div>
              <div className="fc-chip-row">
                <Button variant="secondary" onClick={() => onSelect(job.id)}>
                  Inspect
                </Button>
                {["queued", "running"].includes(job.status) ? (
                  <Button variant="danger" onClick={() => onCancel(job.id)}>
                    Cancel
                  </Button>
                ) : null}
                {job.status === "completed" || job.status === "partial" ? (
                  <Button variant="ghost" onClick={() => onOpenReport(job.id)}>
                    Open report
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="fc-empty">No audit runs are available yet for this workspace.</div>
      )}
    </Card>
  );
}

function StreamPanel({ selectedJob, stream }: { selectedJob: Job | null; stream: StreamEntry[] }) {
  return (
    <Card className="fc-panel">
      <div className="fc-panel-head">
        <div>
          <div className="fc-kicker">Execution stream</div>
          <h2 className="fc-panel-title">Realtime job output</h2>
        </div>
        {selectedJob ? <Badge tone="info">{selectedJob.status}</Badge> : null}
      </div>
      {selectedJob ? (
        <div className="fc-stream">
          {stream.length ? (
            stream.map((entry, index) => (
              <div className="fc-terminal-line" key={`${entry.at}-${index}`}>
                [{entry.event}] {entry.text}
              </div>
            ))
          ) : (
            <div className="fc-terminal-line">Select a queued or running audit to stream live orchestration events.</div>
          )}
        </div>
      ) : (
        <div className="fc-empty">No audit is selected.</div>
      )}
    </Card>
  );
}

function FindingsPanel({
  findings,
  selectedJob,
  search,
  onSearch,
}: {
  findings: Finding[];
  selectedJob: Job | null;
  search: string;
  onSearch: (value: string) => void;
}) {
  return (
    <Card className="fc-panel">
      <div className="fc-panel-head">
        <div>
          <div className="fc-kicker">Finding review</div>
          <h2 className="fc-panel-title">{selectedJob ? formatRepoName(selectedJob.repo_url) : "Choose an audit"}</h2>
        </div>
        <div style={{ minWidth: 240 }}>
          <Input value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search findings, agents, or severity" />
        </div>
      </div>
      {findings.length ? (
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
                <div className="fc-muted">Agent: {finding.agent_source}</div>
                {finding.cvss_score != null ? <div className="fc-muted">CVSS: {finding.cvss_score} {finding.cvss_vector ? `(${finding.cvss_vector})` : ""}</div> : null}
                {finding.evidence ? <div className="fc-copy"><strong>Evidence:</strong> {finding.evidence}</div> : null}
                {finding.remediation ? <div className="fc-copy"><strong>Remediation:</strong> {finding.remediation}</div> : null}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="fc-empty">No findings match the current filter.</div>
      )}
    </Card>
  );
}

function ReportsPanel({ jobs, onOpenReport }: { jobs: Job[]; onOpenReport: (jobId: string) => void }) {
  return (
    <Card className="fc-panel">
      <div className="fc-panel-head">
        <div>
          <div className="fc-kicker">Reports</div>
          <h2 className="fc-panel-title">Completed artifacts</h2>
        </div>
      </div>
      {jobs.length ? (
        <div className="fc-table">
          {jobs.map((job) => (
            <div className="fc-table-row" key={job.id}>
              <div style={{ flex: 1 }}>
                <strong>{formatRepoName(job.repo_url)}</strong>
                <div className="fc-copy" style={{ marginTop: 8 }}>
                  Finished {formatRelativeDate(job.finished_at)}
                </div>
              </div>
              <Button variant="secondary" onClick={() => onOpenReport(job.id)}>
                Open report
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <div className="fc-empty">Completed or partial jobs will appear here with report access.</div>
      )}
    </Card>
  );
}

function SignalsPanel({
  graph,
  graphError,
  insight,
  selectedJob,
}: {
  graph: unknown;
  graphError: string | null;
  insight: AuditInsightResponse | null;
  selectedJob: Job | null;
}) {
  return (
    <div className="fc-grid-2">
      <Card className="fc-panel">
        <div className="fc-panel-head">
          <div>
            <div className="fc-kicker">Attack graph</div>
            <h2 className="fc-panel-title">{selectedJob ? formatRepoName(selectedJob.repo_url) : "Select an audit"}</h2>
          </div>
        </div>
        {graph ? <pre className="fc-json">{JSON.stringify(graph, null, 2)}</pre> : <div className="fc-empty">{graphError ?? "Graph data is not available yet for this job."}</div>}
      </Card>
      <Card className="fc-panel">
        <div className="fc-panel-head">
          <div>
            <div className="fc-kicker">Dashboard insight</div>
            <h2 className="fc-panel-title">Short operator summary</h2>
          </div>
          <Badge tone={insight?.enabled ? "success" : "neutral"}>{insight?.enabled ? "Enabled" : "Disabled"}</Badge>
        </div>
        <div className="fc-empty">{insight?.insight || "No insight is available for the selected audit or the feature flag is off."}</div>
      </Card>
    </div>
  );
}

function LeaderboardPanel({ entries }: { entries: LeaderboardEntry[] }) {
  return (
    <Card className="fc-panel">
      <div className="fc-panel-head">
        <div>
          <div className="fc-kicker">Leaderboard</div>
          <h2 className="fc-panel-title">Top finished scans</h2>
        </div>
      </div>
      {entries.length ? (
        <div className="fc-table">
          {entries.map((entry) => (
            <div className="fc-table-row" key={`${entry.repo_url}-${entry.finished_at}`}>
              <div style={{ flex: 1 }}>
                <strong>{formatRepoName(entry.repo_url)}</strong>
                <div className="fc-copy" style={{ marginTop: 8 }}>
                  {entry.security_score ?? entry.score ?? "No score"} • {formatRelativeDate(entry.finished_at ?? entry.completed_at)}
                </div>
              </div>
              <Badge tone="warning">{entry.critical_count ?? 0} critical</Badge>
            </div>
          ))}
        </div>
      ) : (
        <div className="fc-empty">Leaderboard data becomes available after completed scans accumulate scores.</div>
      )}
    </Card>
  );
}

function ChatPanel({
  enabled,
  messages,
  input,
  onInput,
  onSubmit,
  busy,
  selectedJobId,
}: {
  enabled: boolean;
  messages: ChatMessage[];
  input: string;
  onInput: (value: string) => void;
  onSubmit: () => void;
  busy: boolean;
  selectedJobId: string | null;
}) {
  return (
    <Card className="fc-panel">
      <div className="fc-panel-head">
        <div>
          <div className="fc-kicker">Chat assistant</div>
          <h2 className="fc-panel-title">Ask about the selected audit</h2>
        </div>
        <Badge tone={enabled ? "success" : "neutral"}>{enabled ? "Enabled" : "Disabled"}</Badge>
      </div>
      <div className="fc-findings" style={{ maxHeight: 280 }}>
        {messages.map((message, index) => (
          <div className="fc-finding" key={`${message.role}-${index}`}>
            <div className="fc-muted">{message.role === "assistant" ? "Assistant" : "You"}</div>
            <div className="fc-copy" style={{ marginTop: 8 }}>
              {message.text}
            </div>
          </div>
        ))}
      </div>
      <div className="fc-inline-fields" style={{ marginTop: 16 }}>
        <Input
          value={input}
          onChange={(event) => onInput(event.target.value)}
          placeholder={enabled ? "Summarize the evidence, explain the graph, or suggest next steps." : "Enable LLM_CHAT_ASSISTANT to use this panel."}
          disabled={!enabled || !selectedJobId}
        />
        <Button onClick={onSubmit} loading={busy} disabled={!enabled || !selectedJobId}>
          Ask
        </Button>
      </div>
    </Card>
  );
}

function SettingsPanel({
  authUser,
  systemStatus,
  onPushEnable,
}: {
  authUser: AuthUser | null;
  systemStatus: SystemStatus | null;
  onPushEnable: () => void;
}) {
  return (
    <div className="fc-grid-2">
      <Card className="fc-panel">
        <div className="fc-panel-head">
          <div>
            <div className="fc-kicker">Session profile</div>
            <h2 className="fc-panel-title">Identity and providers</h2>
          </div>
        </div>
        <div className="fc-data-list">
          <div className="fc-copy">Workspace: {authUser?.username ?? "Unknown"}</div>
          <div className="fc-copy">Email: {authUser?.email ?? "Not provided"}</div>
          <div className="fc-copy">Policy version: {authUser?.privacy_policy_version ?? "Unknown"}</div>
          <div className="fc-chip-row">
            <Badge tone={authUser?.providers?.github?.connected ? "success" : "neutral"}>GitHub {authUser?.providers?.github?.connected ? "connected" : "not connected"}</Badge>
            <Badge tone={authUser?.providers?.google?.connected ? "success" : "neutral"}>Google {authUser?.providers?.google?.connected ? "connected" : "not connected"}</Badge>
          </div>
        </div>
      </Card>

      <Card className="fc-panel">
        <div className="fc-panel-head">
          <div>
            <div className="fc-kicker">Runtime settings</div>
            <h2 className="fc-panel-title">Environment signals</h2>
          </div>
        </div>
        <div className="fc-data-list">
          <div className="fc-copy">API: {systemStatus?.api ?? "Unknown"}</div>
          <div className="fc-copy">Database: {systemStatus?.database ?? "Unknown"}</div>
          <div className="fc-copy">Sandbox mode: {systemStatus?.sandbox_mode ?? "Unavailable to this role"}</div>
          <div className="fc-chip-row">
            <Badge tone={systemStatus?.llm_features?.chat_assistant ? "success" : "neutral"}>Chat assistant</Badge>
            <Badge tone={systemStatus?.llm_features?.dashboard_insight ? "success" : "neutral"}>Dashboard insight</Badge>
            <Badge tone={systemStatus?.llm_features?.attack_chain_naming ? "success" : "neutral"}>Attack naming</Badge>
          </div>
          <Button variant="secondary" onClick={onPushEnable}>
            Register push on this device
          </Button>
        </div>
      </Card>
    </div>
  );
}
