# Backend Structure

This document maps the current backend under `backend/app/` and `backend/tests/`.

## `backend/app/api`

Purpose: HTTP route layer for auth, audits, streaming, system status, and artifact access.

Important files:

- `backend/app/api/routes_auth.py`
- `backend/app/api/routes_audit.py`
- `backend/app/api/routes_sse.py`
- `backend/app/api/routes_system.py`
- `backend/app/api/routes_storage.py`
- `backend/app/api/audit_queries.py`

Interactions:

- Depends on `backend/app/services/auth.py` for authentication.
- Depends on `backend/app/models/*` for persistence.
- Dispatches orchestration through `backend/app/orchestrator/runtime.py` or `backend/app/workers/celery_app.py`.

What belongs here:

- Route definitions, request/response wiring, auth dependencies, and route-local validation or access checks.

What should not live here:

- Scanner logic, report rendering, Docker orchestration, or database model definitions.

## `backend/app/agents`

Purpose: repo-analysis and side-effect agents used by the LangGraph pipeline in `backend/app/orchestrator/maestro.py`.

Important files:

- `recon.py`: clone and detect stack
- `sast.py`: regex-based static checks
- `sast_semgrep.py`: Semgrep wrapper with debug fallback
- `dependency_scan.py`: osv-scanner / trivy wrapper with debug fallback
- `api_surface.py`: route discovery heuristics
- `secret_history.py`: committed-secret heuristics
- `authz_idor.py`: route-based authz heuristics
- `network.py`, `attack.py`, `exploit.py`: sandbox-only active stages
- `ai_analyzer.py`: Gemini-backed or debug-fallback triage
- `github_mcp.py`, `google_agent.py`: optional outbound integrations

Interactions:

- Mostly read and write `AuditState` fields through the orchestrator.
- Use services such as `sandbox.py`, `redaction.py`, and `storage.py`.

What belongs here:

- Target-analysis logic and external-tool wrappers that produce findings or downstream side effects.

What should not live here:

- HTTP routing, SQLAlchemy session ownership, or global app startup logic.

## `backend/app/orchestrator`

Purpose: graph definition, runtime state merging, cleanup, scan planning, and terminal-state resolution.

Important files:

- `maestro.py`
- `runtime.py`
- `runtime_context.py`
- `scan_plan.py`

Interactions:

- Imports phase bodies from `backend/app/agents/*` and service-backed phases from `backend/app/services/*`.
- Persists findings and logs to `backend/app/models/*`.

What belongs here:

- Phase ordering, conditional routing, cancellation handling, cleanup, and final status resolution.

What should not live here:

- Low-level route parsing or UI concerns.

## `backend/app/models`

Purpose: SQLAlchemy schema for the persistent data model.

Important files:

- `database.py`: engine/session setup plus compatibility helpers
- `audit_job.py`: jobs, findings, agent logs, artifacts, phase ledger
- `user.py`: users, login failures, user sessions
- `compliance.py`: organizations, memberships, artifact objects, privacy and attestation records
- `security_log.py`: security event records

Interactions:

- Used by API routes, services, and the orchestrator.

What belongs here:

- Persistent schema definitions and DB bootstrap helpers.

What should not live here:

- Route handlers, scanner command execution, or report rendering.

## `backend/app/schemas`

Purpose: Pydantic request/response and runtime-state shapes.

Important files:

- `audit_state.py`: `AuditState`, `JobStatus`, `Severity`, and runtime reducers
- `audit_api.py`: submit payload, job response, finding response

Interactions:

- Shared between API routes and the orchestrator.

What belongs here:

- Typed contracts for runtime state and API I/O.

What should not live here:

- SQLAlchemy models or network side effects.

## `backend/app/services`

Purpose: reusable backend helpers that are not route-specific and not graph-order-specific.

Important files:

- `auth.py`: JWT creation, verification, logout, OAuth state, session revocation
- `sandbox.py`: Docker/Kali lifecycle and mock mode
- `storage.py`: local workspace artifact storage with database metadata
- `reporter.py`: report rendering and email delivery
- `redaction.py`: text and structured data redaction
- `limiter.py`: SlowAPI limiter
- `housekeeping.py`: retention and pruning
- `attack_graph.py`, `remediation_planner.py`, `confidence.py`, `evidence_normalizer.py`

Interactions:

- Shared by routes, orchestrator phases, and some tests.

What belongs here:

- Cross-cutting domain logic with no direct UI or route ownership.

What should not live here:

- Route declarations or persisted schema classes.

## `backend/app/workers`

Purpose: background execution adapters.

Important files:

- `celery_app.py`: Celery app and `run_audit_job_task`
- `scheduler.py`: periodic task hook placeholder

Interactions:

- `routes_audit.py` dispatches to `run_audit_job_task` when Redis is reachable.

Current note:

- `scheduler.py` is not a full scheduled-scan system yet; it contains a placeholder task body.

## `backend/app/config.py`

Purpose: environment-backed settings and production validation.

Current behavior:

- Reads `.env`, `backend/.env`, `.env.local`, and `backend/.env.local`
- Rejects weak production secrets
- Rejects SQLite in non-debug mode
- Rejects scanner image tags ending in `:latest` in non-debug mode

## Tests

Location: `backend/tests/*`

Coverage themes:

- `test_auth.py`: auth, OAuth redirect/callback, policy events, logout
- `test_audit_routes.py`: audit routes, SSE, report safety, system status auth
- `test_maestro.py`, `test_runtime.py`, `test_scan_plan.py`: orchestration and routing
- `test_hardening.py`, `test_startup.py`, `test_config.py`: startup/security/config behavior

The backend test suite is real and currently wired through `pytest.ini` and the root validation script.

---
*Documentation last updated: June 08, 2026*
