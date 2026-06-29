"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { request, ApiError } from "../../lib/request";
import { formatRepoName, formatRelativeDate } from "../../lib/format";
import { AuditInsightResponse, ChatResponse, Job, LeaderboardEntry, SystemStatus } from "../../lib/types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { SiteHeader } from "../SiteChrome";

type ChatMessage = { role: "user" | "assistant"; text: string };

export function SignalsConsole() {
  const searchParams = useSearchParams();
  const requestedJobId = searchParams.get("jobId") ?? searchParams.get("job_id");

  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(requestedJobId);
  const [insight, setInsight] = useState<AuditInsightResponse | null>(null);
  const [graph, setGraph] = useState<unknown>(null);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Ask for a summary of evidence, risk analysis, or next-step guidance for the selected audit.",
    },
  ]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      request<Job[]>("/audit/jobs"),
      request<SystemStatus>("/system/status"),
      request<LeaderboardEntry[]>("/leaderboard").catch(() => []),
    ])
      .then(([nextJobs, status, nextLeaderboard]) => {
        if (!cancelled) {
          setJobs(nextJobs);
          setSystemStatus(status);
          setLeaderboard(nextLeaderboard);
          if (!selectedJobId && nextJobs.length > 0) {
            setSelectedJobId(nextJobs[0].id);
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load initial data.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedJobId]);

  useEffect(() => {
    if (!selectedJobId) return;
    let cancelled = false;

    request<AuditInsightResponse>(`/audit/job/${selectedJobId}/insight`)
      .then((nextInsight) => {
        if (!cancelled) {
          setInsight(nextInsight);
        }
      })
      .catch(() => {
        if (!cancelled) setInsight(null);
      });

    request<unknown>(`/audit/job/${selectedJobId}/graph`)
      .then((nextGraph) => {
        if (!cancelled) {
          setGraph(nextGraph);
          setGraphError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setGraph(null);
          setGraphError(err instanceof ApiError ? err.message : "Attack graph unavailable.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedJobId]);

  async function handleChatSubmit() {
    if (!selectedJobId || !chatInput.trim()) return;

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
        { role: "assistant", text: response.answer ?? response.response ?? "No response was returned." },
      ]);
    } catch (err) {
      setChatMessages((current) => [
        ...current,
        { role: "assistant", text: err instanceof ApiError ? err.message : "Request failed." },
      ]);
    } finally {
      setChatBusy(false);
    }
  }

  const selectedJob = jobs.find((j) => j.id === selectedJobId) ?? null;
  const isChatEnabled = Boolean(systemStatus?.llm_features?.chat_assistant);

  return (
    <div className="fc-page">
      <SiteHeader ctaHref="/dashboard" ctaLabel="Back to Dashboard" />
      <main className="fc-shell fc-dashboard-shell">
        <div className="fc-dashboard-grid">
          <Card className="fc-sidebar">
            <div>
              <div className="fc-kicker">Navigation</div>
              <h2 className="fc-panel-title" style={{ marginTop: 10 }}>Signals & AI</h2>
              <div className="fc-copy" style={{ marginTop: 10 }}>
                Explore advanced attack graphs, insights, and converse with the security agent.
              </div>
            </div>
            <div className="fc-sidebar-nav">
              <Link className="fc-sidebar-tab" href="/dashboard">Dashboard</Link>
              <Link className="fc-sidebar-tab" href="/dashboard/findings">Findings</Link>
              <Link className="fc-sidebar-tab" href="/dashboard/signals" data-active="true">Signals & AI</Link>
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
                    <h2 className="fc-panel-title">{formatRepoName(selectedJob.repo_url)}</h2>
                  ) : (
                    <h2 className="fc-panel-title">No Audit Selected</h2>
                  )}
                </div>

                <div>
                  <select
                    className="fc-input"
                    value={selectedJobId ?? ""}
                    onChange={(e) => startTransition(() => setSelectedJobId(e.target.value || null))}
                    style={{ background: "var(--fc-bg-secondary)", color: "inherit", padding: "8px 12px", border: "1px solid var(--fc-border)" }}
                    aria-label="Select audit run to view signals"
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

            <div className="fc-grid-2">
              <Card className="fc-panel">
                <div className="fc-panel-head">
                  <div>
                    <div className="fc-kicker">Attack Graph</div>
                    <h3 className="fc-panel-title">Visualized exploit chain</h3>
                  </div>
                </div>
                {graph ? (
                  <pre className="fc-json">{JSON.stringify(graph, null, 2)}</pre>
                ) : (
                  <div className="fc-empty">{graphError ?? "No attack graph available."}</div>
                )}
              </Card>

              <Card className="fc-panel">
                <div className="fc-panel-head">
                  <div>
                    <div className="fc-kicker">AI Insight</div>
                    <h3 className="fc-panel-title">Operator overview</h3>
                  </div>
                  <Badge tone={insight?.enabled ? "success" : "neutral"}>
                    {insight?.enabled ? "Active" : "None"}
                  </Badge>
                </div>
                <div className="fc-copy" style={{ whiteSpace: "pre-wrap", minHeight: 120 }}>
                  {insight?.insight || "No summary insight generated for this run."}
                </div>
              </Card>
            </div>

            <Card className="fc-panel">
              <div className="fc-panel-head">
                <div>
                  <div className="fc-kicker">Interactive Assistant</div>
                  <h3 className="fc-panel-title">Ask about this run</h3>
                </div>
                <Badge tone={isChatEnabled ? "success" : "neutral"}>
                  {isChatEnabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>

              <div className="fc-findings" style={{ maxHeight: 300, overflowY: "auto" }}>
                {chatMessages.map((msg, idx) => (
                  <div className="fc-finding" key={idx}>
                    <div className="fc-muted">{msg.role === "assistant" ? "Assistant" : "You"}</div>
                    <div className="fc-copy" style={{ marginTop: 8 }}>{msg.text}</div>
                  </div>
                ))}
              </div>

              <div className="fc-inline-fields" style={{ marginTop: 16 }}>
                <Input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder={isChatEnabled ? "Ask questions about the audit..." : "LLM Chat Assistant is currently disabled."}
                  disabled={!isChatEnabled || !selectedJobId}
                />
                <Button onClick={handleChatSubmit} loading={chatBusy} disabled={!isChatEnabled || !selectedJobId}>
                  Ask
                </Button>
              </div>
            </Card>

            <Card className="fc-panel">
              <div className="fc-panel-head">
                <div>
                  <div className="fc-kicker">Leaderboard</div>
                  <h3 className="fc-panel-title">Top Scans</h3>
                </div>
              </div>
              {leaderboard.length ? (
                <div className="fc-table">
                  {leaderboard.map((entry, index) => (
                    <div className="fc-table-row" key={index}>
                      <div style={{ flex: 1 }}>
                        <strong>{formatRepoName(entry.repo_url)}</strong>
                        <div className="fc-copy" style={{ marginTop: 4 }}>
                          Score: {entry.security_score ?? entry.score ?? "N/A"} • Completed {formatRelativeDate(entry.finished_at ?? entry.completed_at)}
                        </div>
                      </div>
                      <Badge tone="warning">{entry.critical_count ?? 0} critical</Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="fc-empty">No entries in the leaderboard.</div>
              )}
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
