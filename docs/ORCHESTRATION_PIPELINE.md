# Orchestration Pipeline

The current pipeline is defined in `backend/app/orchestrator/maestro.py`. It is not the older "7-stage" graph described by stale docs.

## Exact Node Order

The graph is compiled in this order:

1. `recon`
2. `threat_model`
3. `api_surface`
4. `secret_history`
5. `dependency`
6. `sbom_graph`
7. `iac`
8. `cicd_scan`
9. `container_scan`
10. `config_scan`
11. `sast`
12. `semgrep`
13. `authz_idor`
14. conditional route to `sandbox` or `ai_analyzer`
15. `sandbox`
16. `network`
17. `attack`
18. conditional route to `exploit` or `ai_analyzer`
19. `exploit`
20. `ai_analyzer`
21. `cross_validation`
22. `scoring`
23. `attack_graph`
24. `remediation_planner`
25. `reporter`
26. `github_mcp`
27. `google_agent`
28. `cleanup`

## Graph Diagram

```mermaid
flowchart TD
    START --> recon
    recon --> threat_model
    threat_model --> api_surface
    api_surface --> secret_history
    secret_history --> dependency
    dependency --> sbom_graph
    sbom_graph --> iac
    iac --> cicd_scan
    cicd_scan --> container_scan
    container_scan --> config_scan
    config_scan --> sast
    sast --> semgrep
    semgrep --> authz_idor
    authz_idor -->|"sandbox enabled and no critical secret short-circuit"| sandbox
    authz_idor -->|"sandbox disabled or secret short-circuit"| ai_analyzer
    sandbox --> network
    network --> attack
    attack -->|"dynamic findings present and exploit enabled"| exploit
    attack -->|"no findings or exploit disabled"| ai_analyzer
    exploit --> ai_analyzer
    ai_analyzer --> cross_validation
    cross_validation --> scoring
    scoring --> attack_graph
    attack_graph --> remediation_planner
    remediation_planner --> reporter
    reporter --> github_mcp
    github_mcp --> google_agent
    google_agent --> cleanup
    cleanup --> END
```

## Conditional Routes

Source: `route_after_semgrep()` and `route_after_attack()` in `backend/app/orchestrator/maestro.py`.

### After `authz_idor`

The graph skips active stages and jumps to `ai_analyzer` when either:

- `scan_plan.enabled_scanners` does not include `sandbox`, or
- any `static_findings` or `semgrep_findings` entry is `critical` and has `secret` in its title.

Otherwise it enters `sandbox`.

### After `attack`

The graph jumps directly to `ai_analyzer` when either:

- `scan_plan.enabled_scanners` does not include `exploit`, or
- `dynamic_findings` is empty.

Otherwise it enters `exploit`.

## What Each Phase Reads And Writes

Source: phase bodies in `backend/app/orchestrator/maestro.py` plus helpers in `backend/app/agents/*` and `backend/app/services/*`.

| Phase | Reads | Writes |
| --- | --- | --- |
| `recon` | repo URL, branch, optional GitHub token | clone path, tech stack, entry points, manifests, repo security findings, scan plan |
| `threat_model` | tech stack, entry points, API surface, repo security | threat model with assets, attack vectors, scan recommendations |
| `api_surface` | clone path | detected routes, route risk summary |
| `secret_history` | clone path | secret findings |
| `dependency` | clone path, manifests | dependency findings, scanner execution metadata |
| `sbom_graph` | clone path | SBOM component list, dependency graph summary |
| `iac` | clone path | IaC findings |
| `cicd_scan` | clone path | CI/CD findings |
| `container_scan` | clone path | container findings |
| `config_scan` | clone path, repo URL | configuration file findings (Dockerfile, K8s, Terraform) |
| `sast` | clone path, repo URL | static findings (regex, Bandit, ESLint) |
| `semgrep` | clone path, tech stack | semgrep findings, scanner execution metadata |
| `authz_idor` | detected API surface | authz findings |
| `sandbox` | clone path, entry points, sandbox settings | sandbox IDs, target IP, sandbox execution metadata |
| `network` | sandbox IDs and target IP, API surface | open ports, API endpoints, scanner execution metadata |
| `attack` | sandbox IDs, target IP, open ports | dynamic findings (SQLi, SSRF, XXE, SSTI, JWT, rate limit) |
| `exploit` | sandbox IDs, target IP, dynamic findings | exploit proof findings |
| `ai_analyzer` | accumulated findings | deduplicated findings, false positives, chains, remediations |
| `cross_validation` | static, dynamic, semgrep, dependency, iac findings | validated findings, false positives, correlation report |
| `scoring` | persisted findings | CVSS fields, risk summary |
| `attack_graph` | routes plus selected findings | attack graph, attack chains |
| `remediation_planner` | selected findings | remediation plan and remediation tasks |
| `reporter` | reportable findings, scanner execution | report stored in audit_reports table, HTML snapshot, completed status |
| `github_mcp` | findings, remediations, optional token | GitHub issue/PR metadata |
| `google_agent` | findings, remediations, recipient email | PR risk report, email-delivery metadata |
| `cleanup` | clone path, sandbox identifiers | no new business state, marks cleanup complete |

## Passive vs Active Phases

Passive / repository-only phases:

- `recon`
- `threat_model`
- `api_surface`
- `secret_history`
- `dependency`
- `sbom_graph`
- `iac`
- `cicd_scan`
- `container_scan`
- `config_scan`
- `sast`
- `semgrep`
- `authz_idor`
- `ai_analyzer`
- `cross_validation`
- `scoring`
- `attack_graph`
- `remediation_planner`

Active / sandbox-targeting phases:

- `sandbox`
- `network`
- `attack`
- `exploit`

Outbound integration phases:

- `reporter`
- `github_mcp`
- `google_agent`

## Retry Mechanism

Source: `execute_phase()` in `backend/app/orchestrator/maestro.py`.

- Non-critical phases retry up to 2 times with exponential backoff (1s, 2s delays).
- Retry attempts are logged with warning level.
- `JobCancellationRequested` exceptions bypass retry logic and propagate immediately.

## Sandbox Dependence

Source: `backend/app/orchestrator/scan_plan.py`, `backend/app/services/sandbox.py`.

Active testing is enabled only when all of these are true:

- attestation is accepted
- `authorization_scope == "full_active"`
- Docker is available
- the target repo looks like a supported Python or Node launch profile

In debug mode, sandbox provisioning can fall back to simulation when Docker is unavailable.

## Failure Policy

Source: `NON_CRITICAL_PHASES` in `backend/app/orchestrator/maestro.py`.

Non-critical phases degrade the job to `partial` on exception and allow later phases to continue. That set currently includes:

- `api_surface`
- `secret_history`
- `dependency_scan`
- `sbom_graph`
- `iac_scan`
- `cicd_scan`
- `container_scan`
- `config_scan`
- `semgrep_scan`
- `authz_idor`
- `sandbox`
- `network`
- `attack`
- `exploit`
- `github_mcp`
- `google_agent`
- `threat_model`
- `cross_validation`

Phases outside that list can still fail the orchestration.

## Cleanup Behavior

Source: `cleanup_resources()` in `backend/app/orchestrator/maestro.py` and finalization in `backend/app/orchestrator/runtime.py`.

- Tries to remove the sandbox network, target container, and Kali container.
- Deletes the cloned repository workspace.
- If the graph never reaches `cleanup`, `runtime.py` still forces cleanup in `finally`.

## Cancellation Behavior

Source: `check_cancel_requested()` in `backend/app/orchestrator/maestro.py`, `routes_audit.py`, and `runtime.py`.

- `DELETE /api/v1/audit/job/{job_id}` sets `cancel_requested` and writes an audit log entry.
- The orchestrator checks for cancellation before and after most phases.
- Cancellation raises `JobCancellationRequested`, triggers cleanup, and finalizes the job as `cancelled`.

## Degraded And Simulated Behavior

- `dependency_scan.py` simulates findings in debug mode when scanners are unavailable.
- `sast_semgrep.py` simulates findings in debug mode when `semgrep` is unavailable.
- `sandbox.py` simulates sandbox resources in debug mode when Docker is unavailable or `FIRE_CROW_MOCK_SANDBOX=true`.
- `attack.py` and `exploit.py` mark some findings as `[SIMULATED]` when running in mock sandbox mode.
- `ai_analyzer.py`, `github_mcp.py`, and `google_agent.py` all have debug fallback behavior.
- `reporter.py` can emit HTML plus a placeholder PDF when WeasyPrint is unavailable.
- `config_scan.py` skips scanning for test repositories.

## Known Risks And TODOs

- The frontend submit flow does not currently provide the attestation fields required by the backend.
- `scheduler.py` is still placeholder infrastructure, not a real scheduled-audit subsystem.
- The current scoring phase uses a simple severity-to-CVSS mapping rather than scanner-native scoring.

### Resolved Issues

- [x] GitHub MCP: f-string loggers replaced with lazy `%s` formatting; added error logging when write URL unavailable.
- [x] SAST agent: extended exclude dirs list, expanded binary file skip list, replaced silent `errors='ignore'` with `errors='replace'`.
- [x] Authz/IDOR agent: fixed `db: Any` type to `db: Session`.
- [x] TelemetryMiddleware registered in main.py.
- [x] Neo4j configuration and migration service added.
- [x] API surface scanner: replaced `errors='ignore'` with `errors='replace'`.

---
*Documentation last updated: June 29, 2026*
