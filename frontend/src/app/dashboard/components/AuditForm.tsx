"use client";

import React, { useMemo, useState, useEffect } from "react";
import { GitBranch, Play, ShieldCheck, Search, Loader, CheckSquare, Square, ChevronDown, ChevronUp } from "lucide-react";
import Card from "../../../components/ui/Card";
import Input from "../../../components/ui/Input";
import Button from "../../../components/ui/Button";
import styles from "../page.module.css";
import mobile from "../mobile.module.css";
import { API_BASE_URL } from "../../../lib/policy";

interface GitHubRepo {
  name: string;
  full_name: string;
  html_url: string;
  default_branch: string;
  private: boolean;
}

interface AuditFormProps {
  onSubmit: (repoUrl: string, repoBranch: string) => Promise<void>;
  onBulkSubmit?: (repoUrls: string[], repoBranch: string) => Promise<void>;
  submitting: boolean;
  submitError: string;
  token?: string;
}

export default function AuditForm({ onSubmit, onBulkSubmit, submitting, submitError, token }: AuditFormProps) {
  // Mode: "github" (select from list) or "manual" (type URL)
  const [mode, setMode] = useState<"github" | "manual">("github");
  
  // Manual form state
  const [repoUrl, setRepoUrl] = useState("");
  const [repoBranch, setRepoBranch] = useState("main");
  
  // GitHub Repos state
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoFetchError, setRepoFetchError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
  const [bulkBranch, setBulkBranch] = useState("main");

  const [localError, setLocalError] = useState("");

  // Fetch GitHub repos on load
  useEffect(() => {
    if (!token || mode !== "github") return;
    
    let active = true;
    setLoadingRepos(true);
    setRepoFetchError("");

    async function fetchRepos() {
      try {
        const response = await fetch(`${API_BASE_URL}/audit/github-repos`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw new Error(body?.detail || "Could not load GitHub repositories.");
        }
        const data = await response.json() as GitHubRepo[];
        if (active) {
          setRepos(data);
        }
      } catch (err: any) {
        if (active) {
          setRepoFetchError(err.message || "Failed to fetch repositories.");
          // Fall back to manual mode if we can't fetch repos
          setMode("manual");
        }
      } finally {
        if (active) {
          setLoadingRepos(false);
        }
      }
    }

    void fetchRepos();

    return () => {
      active = false;
    };
  }, [token, mode]);

  const filteredRepos = useMemo(() => {
    return repos.filter(repo => 
      repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.full_name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [repos, searchQuery]);

  const handleToggleSelectRepo = (htmlUrl: string) => {
    setSelectedRepos(prev => 
      prev.includes(htmlUrl) 
        ? prev.filter(url => url !== htmlUrl) 
        : [...prev, htmlUrl]
    );
  };

  const handleSelectAll = () => {
    if (selectedRepos.length === filteredRepos.length) {
      setSelectedRepos([]);
    } else {
      setSelectedRepos(filteredRepos.map(r => r.html_url));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError("");

    if (mode === "manual") {
      const normalizedRepoUrl = repoUrl.trim();
      const normalizedRepoBranch = repoBranch.trim() || "main";

      if (!normalizedRepoUrl) {
        setLocalError("Repository URL is required.");
        return;
      }
      void onSubmit(normalizedRepoUrl, normalizedRepoBranch);
    } else {
      if (selectedRepos.length === 0) {
        setLocalError("Please select at least one repository to audit.");
        return;
      }
      
      const branch = bulkBranch.trim() || "main";
      if (selectedRepos.length === 1) {
        void onSubmit(selectedRepos[0], branch);
      } else if (onBulkSubmit) {
        void onBulkSubmit(selectedRepos, branch);
      } else {
        // Fallback: submit first one
        void onSubmit(selectedRepos[0], branch);
      }
    }
  };

  return (
    <Card variant="surface" className={styles.panel}>
      <div className={styles.panelHeader} style={{ flexWrap: "wrap", gap: "10px" }}>
        <div>
          <div className={styles.sectionKicker}>Intake settings</div>
          <h2>Start security audit</h2>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button 
            type="button"
            className={`${styles.modeButton} ${mode === "github" ? styles.modeButtonActive : ""}`}
            onClick={() => setMode("github")}
            style={{
              padding: "6px 12px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: "bold",
              border: "1px solid var(--border)",
              background: mode === "github" ? "var(--primary)" : "transparent",
              color: mode === "github" ? "var(--bg)" : "var(--text)",
              cursor: "pointer"
            }}
          >
            GitHub Repos
          </button>
          <button 
            type="button"
            className={`${styles.modeButton} ${mode === "manual" ? styles.modeButtonActive : ""}`}
            onClick={() => setMode("manual")}
            style={{
              padding: "6px 12px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: "bold",
              border: "1px solid var(--border)",
              background: mode === "manual" ? "var(--primary)" : "transparent",
              color: mode === "manual" ? "var(--bg)" : "var(--text)",
              cursor: "pointer"
            }}
          >
            Manual URL
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className={styles.auditForm} style={{ marginTop: "16px" }}>
        {mode === "manual" ? (
          <section className={mobile.intakePanel} aria-labelledby="audit-intake-title">
            <div className={mobile.intakeHero}>
              <div className={mobile.intakeIcon} aria-hidden="true">
                <ShieldCheck size={18} />
              </div>
              <div>
                <h3 id="audit-intake-title">Authorized repository intake</h3>
                <p>Submit the GitHub repository URL and branch you want the backend to audit.</p>
              </div>
            </div>

            <div className={mobile.intakeFields} style={{ marginTop: "16px" }}>
              <Input
                label="Repository URL"
                placeholder="https://github.com/org/repository"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                disabled={submitting}
              />
              <Input
                label="Branch or ref"
                placeholder="main"
                value={repoBranch}
                onChange={(e) => setRepoBranch(e.target.value)}
                disabled={submitting}
              />
            </div>

            <div className={mobile.intakeSummary} style={{ marginTop: "16px" }}>
              <div className={mobile.intakeSummaryRow}>
                <span>Repository</span>
                <strong style={{ wordBreak: "break-all" }}>{repoUrl.trim() || "Not set"}</strong>
              </div>
              <div className={mobile.intakeSummaryRow}>
                <span>Branch</span>
                <strong>{repoBranch.trim() || "main"}</strong>
              </div>
            </div>
          </section>
        ) : (
          <section className={mobile.intakePanel}>
            <div className={mobile.intakeHero}>
              <div className={mobile.intakeIcon} aria-hidden="true">
                <GitBranch size={18} />
              </div>
              <div>
                <h3>Select GitHub Repositories</h3>
                <p>Choose one or more connected GitHub repositories to scan concurrently.</p>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "16px", flexWrap: "wrap" }}>
              <div style={{ flexGrow: 1, position: "relative", minWidth: "200px" }}>
                <span style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--muted)" }}>
                  <Search size={14} />
                </span>
                <input
                  type="text"
                  placeholder="Filter repositories..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px 8px 32px",
                    background: "rgba(0,0,0,0.2)",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                    color: "var(--text)",
                    fontSize: "13px"
                  }}
                />
              </div>
              <div style={{ minWidth: "120px" }}>
                <input
                  type="text"
                  placeholder="Branch (e.g. main)"
                  value={bulkBranch}
                  onChange={(e) => setBulkBranch(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    background: "rgba(0,0,0,0.2)",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                    color: "var(--text)",
                    fontSize: "13px"
                  }}
                />
              </div>
            </div>

            {loadingRepos ? (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", padding: "32px 0", gap: "10px", color: "var(--muted)" }}>
                <Loader className={styles.spin} size={16} />
                <span>Fetching repositories from GitHub...</span>
              </div>
            ) : repoFetchError ? (
              <div className={styles.noticeError} style={{ marginTop: "12px" }}>
                {repoFetchError}
              </div>
            ) : filteredRepos.length === 0 ? (
              <div style={{ textAlign: "center", padding: "24px 0", color: "var(--muted)", fontSize: "13px" }}>
                No repositories found matching "{searchQuery}".
              </div>
            ) : (
              <div style={{ marginTop: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "8px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <button
                    type="button"
                    onClick={handleSelectAll}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--primary)",
                      fontSize: "12px",
                      fontWeight: "bold",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px"
                    }}
                  >
                    {selectedRepos.length === filteredRepos.length ? "Deselect All" : "Select All Available"}
                    <span>({selectedRepos.length}/{filteredRepos.length})</span>
                  </button>
                </div>

                <div style={{ maxHeight: "200px", overflowY: "auto", marginTop: "8px", display: "flex", flexDirection: "column", gap: "4px" }}>
                  {filteredRepos.map(repo => {
                    const isSelected = selectedRepos.includes(repo.html_url);
                    return (
                      <button
                        type="button"
                        key={repo.html_url}
                        onClick={() => handleToggleSelectRepo(repo.html_url)}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "8px 10px",
                          background: isSelected ? "rgba(92,144,255,0.08)" : "transparent",
                          border: `1px solid ${isSelected ? "rgba(92,144,255,0.2)" : "transparent"}`,
                          borderRadius: "4px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          cursor: "pointer",
                          color: isSelected ? "var(--text)" : "var(--muted)",
                          fontSize: "13px"
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          {isSelected ? <CheckSquare size={14} className={styles.iconActive} style={{ color: "var(--primary)" }} /> : <Square size={14} />}
                          <span style={{ fontWeight: isSelected ? "bold" : "normal", color: "var(--text)" }}>{repo.full_name}</span>
                          {repo.private && <span style={{ fontSize: "10px", padding: "1px 4px", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>private</span>}
                        </div>
                        <span style={{ fontSize: "11px", opacity: 0.6 }}>branch: {repo.default_branch}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </section>
        )}

        {(localError || submitError) && (
          <div className={styles.noticeError} role="alert" style={{ marginTop: "12px" }}>
            {localError || submitError}
          </div>
        )}

        <div className={mobile.intakeActions} style={{ marginTop: "16px" }}>
          <Button 
            type="submit" 
            variant="primary" 
            loading={submitting} 
            className={styles.submitButton} 
            disabled={submitting || (mode === "manual" ? !repoUrl.trim() : selectedRepos.length === 0)}
          >
            {!submitting && <Play size={14} />}
            {submitting 
              ? "Launching" 
              : mode === "manual" 
                ? "Start audit" 
                : selectedRepos.length > 1 
                  ? `Audit Selected (${selectedRepos.length} Repos)` 
                  : "Audit Selected Repo"
            }
          </Button>
        </div>
      </form>
    </Card>
  );
}
