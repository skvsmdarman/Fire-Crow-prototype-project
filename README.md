# Fire Crow

Fire Crow is a repository-focused security audit prototype with a FastAPI backend, a Next.js frontend, and a LangGraph-based orchestration pipeline. In the current codebase, users authenticate, submit GitHub HTTPS repository URLs, stream audit logs over SSE, and download generated report artifacts. Core sources: `backend/app/main.py`, `backend/app/api/routes_auth.py`, `backend/app/api/routes_audit.py`, `backend/app/orchestrator/maestro.py`, `frontend/src/app/dashboard/page.tsx`.

Fire Crow currently does not present itself honestly as a fully production-ready SaaS scanner. The code includes debug-only simulations, optional Docker-backed dynamic validation, optional Redis/Celery execution, optional object storage, and optional GitHub/Google/email integrations. Several frontend/legal strings still describe stronger compliance or product guarantees than the backend proves today. See [Known Limitations](docs/KNOWN_LIMITATIONS.md).

## Current Status

- Prototype with real local auth, job persistence, log streaming, and report generation.
- Local-first developer workflow with SQLite-friendly debug mode and a combined dev launcher.
- Production hardening is partial, not complete. Production mode rejects weak secrets and SQLite, but many integrations remain optional or degraded. Sources: `backend/app/config.py`, `backend/app/models/database.py`, `backend/app/services/sandbox.py`.

## What Fire Crow Does

- Serves a web UI with landing, sign-in, sign-up, dashboard, legal, and offline pages from `frontend/src/app/*`.
- Exposes auth, audit, system, storage, and health endpoints from `backend/app/api/*` and `backend/app/main.py`.
- Runs a LangGraph pipeline that combines passive analysis stages and, when allowed, sandboxed active testing stages. Source: `backend/app/orchestrator/maestro.py`.
- Persists jobs, findings, logs, artifacts, sessions, security logs, and compliance-oriented records in SQLAlchemy models under `backend/app/models/*`.
- Generates HTML/PDF-style reports and stores them through the storage service. Sources: `backend/app/services/reporter.py`, `backend/app/services/storage.py`.

## What Fire Crow Does Not Do

- It does not guarantee real scanner execution in every environment. Dependency, Semgrep, AI, GitHub, Google, email, and sandbox phases all have config-gated or debug fallback behavior. Sources: `backend/app/agents/dependency_scan.py`, `backend/app/agents/sast_semgrep.py`, `backend/app/agents/ai_analyzer.py`, `backend/app/agents/github_mcp.py`, `backend/app/agents/google_agent.py`, `backend/app/services/sandbox.py`.
- It does not currently prove formal compliance programs such as SOC 2, ISO 27001, GDPR readiness, DPDP readiness, or HIPAA readiness in backend code.
- It does not currently have a frontend audit submission flow that matches the backend attestation contract. The backend requires `attestation_accepted`, while the dashboard does not send it. Sources: `backend/app/schemas/audit_api.py`, `frontend/src/features/audits/api.ts`, `frontend/src/app/dashboard/page.tsx`.

## Architecture Overview

- Frontend: Next.js App Router app in `frontend/src/app/*`.
- Backend: FastAPI app in `backend/app/main.py`.
- Orchestration: LangGraph graph in `backend/app/orchestrator/maestro.py`, runtime finalization in `backend/app/orchestrator/runtime.py`.
- Storage: SQLAlchemy database models in `backend/app/models/*`, local artifact storage in `workspace/storage`, optional R2/S3-compatible object storage through `backend/app/services/storage.py`.
- Background execution: Celery when Redis is reachable, otherwise FastAPI `BackgroundTasks`. Source: `backend/app/api/routes_audit.py`.

See [Architecture](docs/ARCHITECTURE.md) and [Orchestration Pipeline](docs/ORCHESTRATION_PIPELINE.md).

## Backend Overview

- Entry point: `backend/app/main.py`
- Routes: `backend/app/api/routes_auth.py`, `routes_audit.py`, `routes_sse.py`, `routes_system.py`, `routes_storage.py`
- Models: `backend/app/models/audit_job.py`, `user.py`, `compliance.py`, `security_log.py`
- Services: auth, sandbox, storage, reporter, redaction, housekeeping, and supporting planning/graph services in `backend/app/services/*`

## Frontend Overview

- Landing page: `frontend/src/app/page.tsx`
- Sign-in: `frontend/src/app/signin/page.tsx`
- Sign-up: `frontend/src/app/signup/page.tsx`
- Dashboard: `frontend/src/app/dashboard/page.tsx`
- Auth/session storage: `frontend/src/lib/authSession.ts`, `frontend/src/shared/hooks/useAuthSession.ts`
- API client: `frontend/src/shared/api/client.ts`

See [Frontend Structure](docs/FRONTEND_STRUCTURE.md).

## Authentication Overview

- Password login and registration: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`
- Session lookup: `GET /api/v1/auth/me`, `GET /api/v1/auth/session`
- Logout and token revocation: `POST /api/v1/auth/logout`
- Optional OAuth: GitHub and Google callback flows in `backend/app/api/routes_auth.py`
- Tokens are JWT bearer tokens, also accepted from a cookie named by `AUTH_COOKIE_NAME`. Source: `backend/app/services/auth.py`

## Data And Storage Overview

- Jobs, findings, logs, artifacts, sessions, and compliance records are stored in the configured database. Sources: `backend/app/models/*`
- Reports and large evidence artifacts are stored through `backend/app/services/storage.py`, with local filesystem fallback when object storage is unavailable.
- Health probes also test local storage and optional object storage. Source: `backend/app/main.py`

See [Data Flow And Storage](docs/DATA_FLOW_AND_STORAGE.md).

## Local Setup

1. Create a Python virtual environment at `.venv` and install `backend/requirements.txt`.
2. Install frontend dependencies in `frontend/`.
3. Copy `backend/.env.example` to `backend/.env.local`.
4. Copy `frontend/.env.example` to `frontend/.env.local` if you are not using the repo launcher.
5. Run `npm run dev` from the repository root.

Detailed instructions: [Local Development](docs/LOCAL_DEVELOPMENT.md).

## Development Commands

```powershell
npm run dev
npm run dev:no-worker
npm run smoke
npm run validate
```

Relevant scripts live in `package.json`, `scripts/dev.py`, `scripts/smoke.py`, and `scripts/validate.py`.

## Test And Validation Commands

```powershell
npm run validate
.\.venv\Scripts\python.exe -m pytest backend/tests
cd frontend; npm run lint
cd frontend; npm run build
```

See [Testing And Validation](docs/TESTING_AND_VALIDATION.md).

## Key API Endpoints

| Endpoint | Purpose | Source |
| --- | --- | --- |
| `GET /health` | basic API and DB probe | `backend/app/main.py` |
| `GET /health/live` | liveness probe | `backend/app/main.py` |
| `GET /health/ready` | readiness probe with DB and Redis check | `backend/app/main.py` |
| `GET /health/deep` | deep probe with storage checks | `backend/app/main.py` |
| `POST /api/v1/auth/login` | password login | `backend/app/api/routes_auth.py` |
| `POST /api/v1/auth/register` | workspace registration | `backend/app/api/routes_auth.py` |
| `GET /api/v1/system/status` | authenticated status payload | `backend/app/api/routes_system.py` |
| `POST /api/v1/audit/submit` | create an audit job | `backend/app/api/routes_audit.py` |
| `GET /api/v1/audit/{job_id}/stream` | SSE log stream | `backend/app/api/routes_sse.py` |

Full route details: [API Reference](docs/API_REFERENCE.md).

## Repository Layout

```text
backend/
  app/
    api/
    agents/
    models/
    orchestrator/
    schemas/
    services/
    workers/
  tests/
frontend/
  src/
    app/
    components/
    features/
    lib/
    shared/
scripts/
workspace/
docs/
```

## Security And Authorization Notice

Fire Crow is written for authorization-only scanning. The backend records an authorization attestation on audit submission and the orchestrator only enables active stages when attestation, authorization scope, Docker availability, and target profile all line up. Sources: `backend/app/schemas/audit_api.py`, `backend/app/api/routes_audit.py`, `backend/app/orchestrator/scan_plan.py`.

That said, the current frontend does not yet send the attestation fields required by the backend, so the current dashboard submission flow is out of sync with the real API contract.

## Known Limitations

- Debug mode can simulate scanners and email/report paths instead of proving them.
- The dashboard audit submission flow is currently out of sync with the backend schema.
- The smoke script currently does not match the current auth and attestation requirements.
- Legal/policy content in the frontend makes claims that are not fully backed by server-side implementation.

See [Known Limitations](docs/KNOWN_LIMITATIONS.md), [Deployment Notes](docs/DEPLOYMENT_NOTES.md), and [Security Model](docs/SECURITY_MODEL.md).

## Documentation

- [Documentation Index](docs/INDEX.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Backend Structure](docs/BACKEND_STRUCTURE.md)
- [Orchestration Pipeline](docs/ORCHESTRATION_PIPELINE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Local Development](docs/LOCAL_DEVELOPMENT.md)

