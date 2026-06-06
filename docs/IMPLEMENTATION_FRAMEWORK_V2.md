# Fire Crow v2 — Implementation Framework

> Gap analysis, military-grade hardening plan, and agentic MCP integration roadmap.

---

## PART 1: GAP ANALYSIS — Current Backend

### 1.1 Critical Scanning Gaps

| Gap ID | Current State | What's Missing | Impact |
|:-------|:-------------|:---------------|:-------|
| **G-01** | SAST uses 4 regex patterns | No Semgrep, no Bandit, no real AST parsing | Misses 90%+ of real vulnerabilities |
| **G-02** | No dependency CVE scanning | No Trivy, no Snyk, no Safety, no OSV | Can't detect known CVEs in `package.json` / `requirements.txt` |
| **G-03** | No SBOM generation | No CycloneDX / SPDX output | Can't produce software bill of materials for compliance |
| **G-04** | No IaC scanning | No Checkov, no tfsec | Terraform/CloudFormation/K8s misconfigs go undetected |
| **G-05** | No container image scanning | No Trivy image scan, no Grype | Dockerfile base images with CVEs pass through |
| **G-06** | No API schema analysis | No OpenAPI/Swagger vuln detection | Auth bypass, broken access control, mass assignment invisible |
| **G-07** | Scoring is static mapping | `CRITICAL→9.8, HIGH→8.5, MEDIUM→5.0` hardcoded | No real CVSS vector calculation, no context-aware risk |
| **G-08** | No LLM-powered analysis | Agents are deterministic scripts | Can't reason about business logic flaws, auth flows, or chained vulns |
| **G-09** | GitHub MCP only creates issues | No PR creation, no branch, no fix suggestions | User asked for PRs with remediation code |
| **G-10** | No secret rotation detection | Only finds secrets, doesn't check if rotated | False positives on already-rotated credentials |

### 1.2 Platform Security Gaps (Fire Crow Itself)

| Gap ID | Vulnerability | Severity | Current State |
|:-------|:-------------|:--------:|:-------------|
| **S-01** | CORS allows all origins | HIGH | `allow_origins=["*"]` in main.py |
| **S-02** | No rate limiting | HIGH | Unlimited login attempts + job submissions |
| **S-03** | No input validation on `repo_url` | CRITICAL | Any string accepted — SSRF via `git clone` to internal IPs |
| **S-04** | No request body size limits | MEDIUM | Unbounded POST payloads |
| **S-05** | No CSP/security headers | MEDIUM | Missing X-Frame-Options, X-Content-Type, HSTS |
| **S-06** | Reports served without auth | HIGH | Mitigated by authenticated `/api/v1/audit/job/{id}/report` and safe report URL validation |
| **S-07** | No encryption at rest | HIGH | Findings/evidence stored as plaintext in SQLite/PostgreSQL |
| **S-08** | No RBAC | MEDIUM | All users have equal permissions |
| **S-09** | JWT uses HS256 | MEDIUM | Should use RS256/ES256 with key rotation |
| **S-10** | No audit trail for admin actions | HIGH | No log of who accessed what findings |
| **S-11** | Clone path traversal risk | CRITICAL | Malicious repo could contain symlinks escaping workspace |
| **S-12** | No sandbox escape prevention | CRITICAL | Cloned repo's Dockerfile could mount host volumes |
| **S-13** | Celery broker has no auth | HIGH | Redis with no password by default |
| **S-14** | No webhook signature validation | MEDIUM | GitHub MCP calls have no HMAC verification |
| **S-15** | No database connection encryption | HIGH | No SSL/TLS enforced on PostgreSQL connection |

### 1.3 Agentic Workflow Gaps

| Gap | Description |
|:----|:-----------|
| No LLM integration | Agents run deterministic scripts only — no reasoning |
| No tool chaining | Each agent is isolated; can't call other tools dynamically |
| No memory/context | Agents don't learn from past scans of the same repo |
| No false positive filtering | Every regex match becomes a finding |
| No remediation generation | Can't suggest or write fix code |
| No multi-language support | Regex patterns mostly target Python |

---

## PART 2: MILITARY-GRADE HARDENING PLAN

### Phase H1 — Network & Transport Layer

```
1. CORS lockdown
   - allow_origins = [settings.FRONTEND_URL]  # explicit whitelist
   - allow_credentials = True only with explicit origins

2. Security headers middleware
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - Strict-Transport-Security: max-age=31536000; includeSubDomains
   - Content-Security-Policy: default-src 'self'
   - Referrer-Policy: strict-origin-when-cross-origin
   - X-Request-ID: {uuid} on every response (for tracing)

3. TLS enforcement
   - PostgreSQL: sslmode=require in DATABASE_URL
   - Redis: rediss:// URL with TLS certificates
   - All external API calls: verify=True (no cert skip)
```

### Phase H2 — Input Validation & SSRF Prevention

```
1. repo_url validation (new Pydantic validator on SubmitJobRequest):
   - Must match: ^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+(\.git)?$
   - Block: private IPs (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x)
   - Block: non-GitHub hosts (configurable allowlist for GitLab/Bitbucket)
   - Block: file://, ssh://, ftp:// schemes
   - Maximum URL length: 2048 chars

2. repo_branch validation:
   - Must match: ^[a-zA-Z0-9._/-]+$
   - Max length: 255 chars

3. Request body size limits:
   - Add middleware: max body = 1MB for API, 0 for GET requests

4. Clone path hardening:
   - After clone: scan for symlinks pointing outside workspace
   - Remove .git/hooks/ directory (prevents hook execution)
   - Set clone directory permissions to read-only after clone
```

### Phase H3 — Authentication & Authorization Hardening

```
1. JWT upgrade:
   - Algorithm: RS256 (asymmetric key pair)
   - Key rotation: new key pair monthly, old keys valid for 48h overlap
   - Token expiry: 1 hour (access), 7 days (refresh)
   - Add refresh token rotation with one-time-use enforcement

2. Rate limiting (new middleware):
   - /auth/login: 5 attempts per IP per 15 minutes
   - /auth/register: 3 per IP per hour
   - /audit/submit: 10 per user per hour
   - SSE streams: 5 concurrent per user
   - Global: 100 req/min per IP

3. RBAC model:
   - Roles: viewer, auditor, admin
   - viewer: read jobs/findings only
   - auditor: submit jobs + read
   - admin: cancel jobs + manage users + view all tenants

4. Report access control:
   - Remove static file mount for /reports/
   - Replace with authenticated endpoint: GET /api/v1/audit/job/{id}/report
   - Verify job ownership before streaming file
```

### Phase H4 — Data Protection

```
1. Encryption at rest:
   - Findings.evidence: AES-256-GCM encrypted before DB insert
   - Findings.remediation: AES-256-GCM encrypted
   - Encryption key from env: FINDINGS_ENCRYPTION_KEY (separate from SECRET_KEY)
   - Key rotation: re-encrypt on key change via migration script

2. Database hardening:
   - PostgreSQL: enforce SSL, use scram-sha-256 auth
   - Connection pooling: pgBouncer with connection limits
   - Prepared statements only (SQLAlchemy default)
   - Row-level security policies for tenant isolation

3. Secrets management:
   - Move all secrets to HashiCorp Vault or AWS Secrets Manager
   - Never log secret values (redact in all log formatters)
   - Auto-rotate GITHUB_TOKEN, RESEND_API_KEY monthly
```

### Phase H5 — Sandbox Isolation

```
1. Docker security:
   - Run containers with --read-only filesystem
   - Drop ALL capabilities: --cap-drop=ALL
   - No new privileges: --security-opt=no-new-privileges
   - Memory limit: --memory=512m per container
   - CPU limit: --cpus=0.5 per container
   - PID limit: --pids-limit=100
   - Network: no internet access from sandbox (internal bridge only)
   - Never mount host directories writable

2. Dockerfile build safety:
   - NEVER build user-supplied Dockerfiles directly
   - Use a pre-built base image only
   - Copy source into read-only volume
   - Run as non-root user inside container

3. Clone workspace isolation:
   - chroot or namespace the clone directory
   - Remove execute permission on all cloned files
   - Time-bomb: auto-delete clone after 30 minutes regardless of job status
```

### Phase H6 — Audit Trail & Monitoring

```
1. Security audit log table (new):
   - who (user_id), what (action), when (timestamp), where (IP, user-agent)
   - Actions: login, register, submit_job, view_findings, download_report, cancel_job
   - Immutable: append-only, no DELETE permission on this table

2. Anomaly detection:
   - Alert on: >5 failed logins from same IP
   - Alert on: user submitting >20 jobs/day
   - Alert on: job scanning internal/private IP ranges

3. OpenTelemetry integration:
   - Trace every agent execution duration
   - Metric: findings_count_by_severity gauge
   - Metric: job_duration_seconds histogram
   - Export to Grafana/Prometheus stack
```

---

## PART 3: AGENTIC MCP INTEGRATION ROADMAP

### 3.1 Open-Source MCP Servers to Integrate

| MCP Server | Purpose | Integration Point |
|:-----------|:--------|:-----------------|
| **Semgrep MCP** | Real AST-based SAST scanning | Replace regex SAST agent |
| **Trivy MCP** | Dependency CVE + container image + IaC scanning | New DEPENDENCY_SCAN + CONTAINER_SCAN agents |
| **Snyk MCP** | Deep SCA + code analysis + license compliance | Parallel to Trivy for cross-validation |
| **Bandit MCP** | Python-specific security linting | Supplement SAST for Python repos |
| **GitMCP** (`gitmcp.io`) | Read repo docs + raise issues/PRs | Already integrated, extend for PRs |
| **GitHub MCP** (`github.com/modelcontextprotocol`) | Full GitHub API (create branch, commit, PR) | New PR_GENERATOR agent |
| **Nuclei MCP** | Template-based vuln scanning | Replace current mock nuclei calls |
| **Checkov MCP** | IaC policy scanning | New IAC_SCAN agent |

### 3.2 New Agent Architecture

```
Current Pipeline (8 agents):
  RECON → SAST → SANDBOX → NETWORK → ATTACK → EXPLOIT → SCORING → REPORTER

Proposed Pipeline (14 specialized agents):

  ┌─ Phase 1: Intelligence Gathering ──────────────────────────┐
  │  RECON          → Clone + tech stack + SBOM generation     │
  │  DEPENDENCY_SCAN → Trivy/Snyk CVE scan on manifests        │
  │  IAC_SCAN       → Checkov on Terraform/K8s/Docker configs  │
  └────────────────────────────────────────────────────────────┘
           ↓
  ┌─ Phase 2: Static Analysis ────────────────────────────────┐
  │  SAST_SEMGREP   → Semgrep MCP with OWASP/CWE rulesets     │
  │  SAST_SECRETS   → Gitleaks MCP + TruffleHog for secrets    │
  │  SAST_BANDIT    → Python-specific security linting         │
  └────────────────────────────────────────────────────────────┘
           ↓
  ┌─ Phase 3: Dynamic Analysis (conditional) ─────────────────┐
  │  SANDBOX        → Hardened Docker provisioning             │
  │  NETWORK        → Nmap + service fingerprinting            │
  │  ATTACK         → Sqlmap + Nuclei + ZAP                    │
  │  EXPLOIT        → PoC verification + evidence collection   │
  └────────────────────────────────────────────────────────────┘
           ↓
  ┌─ Phase 4: AI Reasoning ───────────────────────────────────┐
  │  AI_ANALYZER    → LLM reviews all findings:                │
  │                   - Deduplicate across agents               │
  │                   - Filter false positives                  │
  │                   - Identify chained attack paths           │
  │                   - Generate remediation code snippets      │
  │                   - Calculate real CVSS vectors             │
  └────────────────────────────────────────────────────────────┘
           ↓
  ┌─ Phase 5: Delivery ──────────────────────────────────────┐
  │  SCORING        → Final CVSS scoring with AI context       │
  │  REPORTER       → PDF + email                              │
  │  GITHUB_MCP     → Create issue + branch + PR with fixes    │
  └────────────────────────────────────────────────────────────┘
```

### 3.3 AI_ANALYZER Agent — The Brain

This is the most critical new agent. It uses LLM (Gemini/OpenAI) to:

```python
# Responsibilities:
1. DEDUPLICATION
   - Multiple agents may flag the same issue (Semgrep + regex both find SQL injection)
   - LLM clusters similar findings and keeps the most detailed one

2. FALSE POSITIVE FILTERING
   - Regex found "password" in a comment? LLM reads context and dismisses it
   - Secret found in test fixtures? LLM checks if it's a real credential

3. ATTACK CHAIN ANALYSIS
   - "SQL injection in /api/users" + "No auth on /api/admin" = privilege escalation chain
   - LLM connects dots across multiple finding sources

4. REMEDIATION CODE GENERATION
   - For each confirmed finding, LLM generates a code diff
   - Example: replaces f-string SQL with parameterized query
   - Output: list of {file_path, original_code, fixed_code}

5. CONTEXTUAL CVSS SCORING
   - Instead of static severity→score mapping
   - LLM evaluates: attack vector, complexity, required privileges, user interaction
   - Generates proper CVSS:3.1 vector strings
```

### 3.4 GITHUB_MCP v2 — Full PR Workflow

```
Current: Creates an issue only

Proposed flow:
  1. Create branch: "firecrow/security-fixes-{job_id}"
  2. For each AI_ANALYZER remediation:
     - Read file from repo via GitMCP
     - Apply code fix
     - Commit with message: "fix(security): {finding.title} [CWE-{id}]"
  3. Create PR:
     - Title: "🔒 Fire Crow Security Fixes — {N} vulnerabilities"
     - Body: Markdown report with all findings + fixes
     - Labels: ["security", "automated"]
     - Reviewers: repo CODEOWNERS
  4. Create issue (if PR creation fails):
     - Fallback to current issue-only behavior
```

### 3.5 MCP Client Architecture

```python
# backend/app/services/mcp_client.py

class MCPClientPool:
    """Manages connections to multiple MCP servers."""

    servers = {
        "semgrep": "https://mcp.semgrep.dev",
        "trivy": "stdio://trivy-mcp-server",
        "gitmcp": "https://gitmcp.io/{owner}/{repo}",
        "github": "stdio://github-mcp-server",
    }

    async def call_tool(self, server: str, tool: str, args: dict) -> dict:
        """Route tool calls to the appropriate MCP server."""
        # SSE-based servers: HTTP POST to discovered endpoint
        # stdio-based servers: subprocess with JSON-RPC over stdin/stdout
```

---

## PART 4: UPDATED LANGGRAPH STATE SCHEMA

```python
class AuditState(BaseModel):
    # --- Job Identity ---
    job_id: str = ""
    user_id: str = ""
    repo_url: str = ""
    repo_branch: str = ""
    repo_owner: str = ""          # NEW: parsed from repo_url
    repo_name: str = ""           # NEW: parsed from repo_url

    # --- Phase 1: Intelligence ---
    clone_path: str = ""
    tech_stack: list[str] = []
    entry_points: list[str] = []
    dependency_manifests: list[str] = []
    sbom: dict = {}               # NEW: CycloneDX SBOM
    dependency_vulns: list[Finding] = []  # NEW: Trivy/Snyk CVE results
    iac_findings: list[Finding] = []      # NEW: Checkov results

    # --- Phase 2: Static Analysis ---
    semgrep_findings: list[Finding] = []  # NEW: Semgrep results
    secret_findings: list[Finding] = []   # NEW: separated from generic SAST
    bandit_findings: list[Finding] = []   # NEW: Python-specific
    static_findings: list[Finding] = []   # KEPT: aggregated

    # --- Phase 3: Dynamic ---
    # (same as current)

    # --- Phase 4: AI Reasoning ---
    deduplicated_findings: list[Finding] = []  # NEW
    false_positives: list[str] = []            # NEW: IDs of dismissed findings
    attack_chains: list[dict] = []             # NEW: chained vuln paths
    remediations: list[dict] = []              # NEW: {file, original, fixed}

    # --- Phase 5: Delivery ---
    github_pr_url: str = ""       # NEW: PR URL
    github_branch: str = ""       # NEW: fix branch name
```

---

## PART 5: IMPLEMENTATION MILESTONES

### Milestone 1 — Hardening (Week 1-2)
Priority: Make Fire Crow itself unhackable.

| Task | Files to Change |
|:-----|:---------------|
| CORS lockdown + security headers middleware | `main.py` |
| `repo_url` SSRF validation | `schemas/audit_api.py`, `agents/recon.py` |
| Rate limiting middleware (slowapi) | `main.py`, new `middleware/rate_limit.py` |
| Authenticated report downloads | `routes_audit.py` (remove static mount) |
| Clone path symlink sanitization | `agents/recon.py` |
| Sandbox Docker hardening flags | `services/sandbox.py` |
| Security audit log table | new `models/security_log.py` |
| Redis auth + TLS | `config.py`, `.env.example` |
| PostgreSQL SSL enforcement | `models/database.py` |

### Milestone 2 — Real Scanning (Week 3-4)
Priority: Replace mock/regex agents with real tools.

| Task | Files to Create/Change |
|:-----|:----------------------|
| Semgrep MCP client integration | new `agents/sast_semgrep.py` |
| Trivy dependency scan agent | new `agents/dependency_scan.py` |
| Gitleaks/TruffleHog secret scanner | refactor `agents/sast.py` |
| Checkov IaC scanner agent | new `agents/iac_scan.py` |
| SBOM generator (CycloneDX) | extend `agents/recon.py` |
| Update LangGraph with new nodes | `orchestrator/maestro.py` |
| Update AuditState schema | `schemas/audit_state.py` |

### Milestone 3 — AI Brain (Week 5-6)
Priority: Add LLM-powered reasoning.

| Task | Files to Create/Change |
|:-----|:----------------------|
| AI_ANALYZER agent (Gemini/OpenAI) | new `agents/ai_analyzer.py` |
| Finding deduplication logic | inside `ai_analyzer.py` |
| False positive filtering | inside `ai_analyzer.py` |
| Attack chain detection | inside `ai_analyzer.py` |
| Remediation code generation | inside `ai_analyzer.py` |
| Contextual CVSS scoring | refactor `maestro.py:scoring_body` |

### Milestone 4 — GitHub PR Automation (Week 7)
Priority: Auto-fix repos with PRs.

| Task | Files to Create/Change |
|:-----|:----------------------|
| GitHub MCP v2: branch + commit + PR | refactor `agents/github_mcp.py` |
| GitMCP file read integration | extend `agents/github_mcp.py` |
| PR body markdown generator | extend `agents/github_mcp.py` |
| Webhook for PR review status | new `api/routes_webhook.py` |

### Milestone 5 — Enterprise Features (Week 8+)
Priority: SaaS readiness.

| Task | Files to Create/Change |
|:-----|:----------------------|
| RBAC with roles table | new `models/role.py`, refactor `services/auth.py` |
| Multi-org tenant model | extend `models/user.py` |
| Scheduled recurring scans | new `workers/scheduler.py` |
| Findings encryption at rest | new `services/crypto.py` |
| OpenTelemetry tracing | new `middleware/telemetry.py` |
| Compliance report export (SOC2/ISO) | extend `services/reporter.py` |

---

## PART 6: AGENT SKILL MATRIX

Each agent needs specific tooling and expertise:

| Agent | Tools Required | MCP Server | Language Skills | Security Domain |
|:------|:-------------|:-----------|:---------------|:---------------|
| **RECON** | git, syft (SBOM) | GitMCP | All | Asset discovery |
| **DEPENDENCY_SCAN** | trivy, snyk, safety | Trivy MCP, Snyk MCP | All manifests | SCA (CVE-2024-*) |
| **IAC_SCAN** | checkov, tfsec | Checkov MCP | HCL, YAML, JSON | Cloud misconfiguration |
| **SAST_SEMGREP** | semgrep | Semgrep MCP | Python, JS, Go, Java | OWASP Top 10 code |
| **SAST_SECRETS** | gitleaks, trufflehog | — (CLI) | All | CWE-798 credential leak |
| **SAST_BANDIT** | bandit | Bandit MCP | Python only | PEP-506, CWE-78/89/95 |
| **SANDBOX** | Docker SDK | — (local) | Dockerfile | Container security |
| **NETWORK** | nmap, masscan | Security Hub MCP | — | CWE-200 info disclosure |
| **ATTACK** | sqlmap, nuclei, zap | Security Hub MCP | — | OWASP Top 10 dynamic |
| **EXPLOIT** | sqlmap, metasploit, curl | Security Hub MCP | — | Proof of concept |
| **AI_ANALYZER** | Gemini/OpenAI API | — (direct API) | All | Reasoning + dedup + fix |
| **SCORING** | CVSS calculator | — (library) | — | Risk quantification |
| **REPORTER** | WeasyPrint, Resend | — (library) | — | Compliance reporting |
| **GITHUB_MCP** | GitHub API, gitmcp.io | GitMCP + GitHub MCP | All | Automated remediation |

---

## PART 7: SECURITY THREAT MODEL (Fire Crow as Target)

### Attack Surface Map

```
                    ┌─────────────────────────────────┐
                    │         ATTACK VECTORS           │
                    └─────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   [API Layer]          [Clone Layer]         [Sandbox Layer]
        │                     │                     │
   ● SSRF via repo_url   ● Malicious repo      ● Container escape
   ● SQL injection       ● Git hook execution   ● Network pivot
   ● Auth bypass         ● Symlink traversal    ● Host mount abuse
   ● Rate limit abuse    ● Zip bomb / repo bomb ● Resource exhaustion
   ● JWT forgery         ● Submodule attack     ● Crypto mining
        │                     │                     │
        ▼                     ▼                     ▼
   [Data Layer]          [MCP Layer]           [Output Layer]
        │                     │                     │
   ● DB injection        ● Tool poisoning      ● Report XSS
   ● Evidence exfil      ● MITM on SSE         ● Email injection
   ● Tenant crossing     ● Token passthrough    ● PDF exploit
```

### Mitigations Required

| Threat | Mitigation | Implementation |
|:-------|:-----------|:--------------|
| SSRF via repo_url | URL allowlist + DNS resolution check | Pydantic validator + pre-clone DNS lookup |
| Malicious git hooks | Delete `.git/hooks/` after clone | Post-clone sanitizer in recon.py |
| Repo bomb (100GB repo) | `--depth 1` + disk quota check | Already have depth=1; add `du` check post-clone |
| Symlink escape | Scan for symlinks pointing outside workspace | Post-clone `os.walk` + `os.path.realpath` check |
| Container escape | Drop caps, read-only FS, no-new-privileges | Docker run flags in sandbox.py |
| Tenant data crossing | Row-level security + query filter | Already filtered; add DB-level RLS policies |
| JWT forgery | RS256 + key rotation | Replace HS256 in auth.py |
| Tool poisoning via MCP | Validate MCP responses, never eval() | Response schema validation in mcp_client.py |
| Report XSS | Sanitize all finding fields in HTML | HTML-escape before template injection |
| Evidence exfiltration | Encrypt at rest + access logging | AES-256-GCM + security audit log |

---

## PART 8: QUICK-WIN CHECKLIST

These can be implemented immediately with minimal code changes:

- [ ] **CORS**: Change `allow_origins=["*"]` → `allow_origins=[settings.FRONTEND_URL]`
- [ ] **repo_url regex**: Add Pydantic validator to `SubmitJobRequest`
- [ ] **Git hooks removal**: Add `shutil.rmtree(os.path.join(target_dir, ".git", "hooks"))` after clone
- [ ] **Symlink check**: Add post-clone `os.walk` to reject repos with external symlinks
- [x] **Report auth**: Replace `/reports/` static mount with authenticated endpoint
- [ ] **Security headers**: Add `Starlette` middleware with CSP/HSTS/X-Frame
- [ ] **Rate limiting**: Install `slowapi` and add decorators to auth + submit endpoints
- [ ] **Clone size limit**: Check `du -s` after clone, reject if >500MB
- [x] **HTML escape findings**: `html.escape()` all finding fields before reporter template
- [ ] **Redis password**: Add `REDIS_PASSWORD` to config, use in connection URL
