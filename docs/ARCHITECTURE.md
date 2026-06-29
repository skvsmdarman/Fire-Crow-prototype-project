# Architecture

This document describes the current repository shape backed by `backend/app/main.py`, `backend/app/orchestrator/maestro.py`, `backend/app/services/*`, and `frontend/src/app/*`.

## High-Level Diagram

```mermaid
flowchart TD
    Browser["Browser / PWA shell"] --> Ingress["Nginx Load Balancer\n/ AWS ALB Ingress"]
    Ingress --> Frontend["Next.js frontend\nfrontend/src/app/*"]
    Ingress --> API["FastAPI app replicas\nbackend/app/main.py"]
    API --> TenantMW["TenantMiddleware\nbackend/app/middleware/tenant.py"]
    TenantMW --> MFAEnforce["MFA Enforcement\nbackend/app/middleware/mfa_enforcement.py"]
    MFAEnforce --> Auth["Auth & SSO routes\nbackend/app/api/routes_auth.py\n/routes_sso.py"]
    MFAEnforce --> MFA["MFA & security routes\nbackend/app/api/routes_mfa.py"]
    MFAEnforce --> IAM["IAM & PAM routes\nbackend/app/api/routes_iam.py\n/routes_pam.py"]
    MFAEnforce --> Audit["Audit & Jobs routes\nbackend/app/api/routes_audit.py"]
    MFAEnforce --> SSE["SSE route\nbackend/app/api/routes_sse.py"]
    MFAEnforce --> System["System & health routes\nbackend/app/api/routes_system.py"]
    Audit --> Dispatch{"Redis reachable?"}
    Dispatch -- "yes" --> Celery["Celery worker cluster\nbackend/app/workers/celery_app.py"]
    Dispatch -- "no" --> BG["FastAPI BackgroundTasks\nbackend/app/api/routes_audit.py"]
    Celery --> Runtime["Runtime finalizer\nbackend/app/orchestrator/runtime.py"]
    BG --> Runtime
    Runtime --> Graph["LangGraph pipeline\nbackend/app/orchestrator/maestro.py"]
    Graph --> DB["SQLAlchemy database\nbackend/app/models/*"]
    Graph --> Local["Local workspace files\nworkspace/reports\nworkspace/storage"]
    Graph --> R2["Optional R2/S3 storage\nbackend/app/services/storage.py"]
    Graph --> Sandbox["Optional Docker/Kali sandbox\nbackend/app/services/sandbox.py"]
    Graph --> Email["Optional email delivery\nbackend/app/services/reporter.py"]
    Graph --> GitHub["Optional GitHub/GitMCP actions\nbackend/app/agents/github_mcp.py"]
```

## Request Flow

1. The browser loads UI routes from `frontend/src/app/*`. In containerized deployment, `backend/app/main.py` can mount `frontend/out` at `/`.
2. Frontend API calls go through `frontend/src/shared/api/client.ts`, which uses `NEXT_PUBLIC_API_URL` or a localhost fallback.
3. Authenticated calls carry a bearer token from `frontend/src/lib/authSession.ts`; the backend also accepts the auth cookie in `backend/app/services/auth.py`.
4. `backend/app/main.py` applies request-size checks, request IDs, security headers, CORS, and SlowAPI rate limiting before routing.

## Audit Job Lifecycle

Source paths: `backend/app/api/routes_audit.py`, `backend/app/orchestrator/runtime.py`, `backend/app/orchestrator/maestro.py`, `backend/app/models/audit_job.py`.

1. `POST /api/v1/audit/submit` validates the request, enforces the per-user active job cap, creates an `AuditJob`, and writes an `AuthorizationAttestation`.
2. The route dispatches work to Celery when Redis is reachable or to FastAPI `BackgroundTasks` otherwise.
3. `execute_audit_job()` initializes `AuditState`, restores GitHub token context from the user record, and invokes the compiled LangGraph.
4. Each phase writes `AgentLog` rows and `PhaseLedgerModel` rows.
5. The orchestrator includes retry mechanisms with exponential backoff for transient failures in non-critical phases.
6. Final status is resolved in `backend/app/orchestrator/runtime.py` as `completed`, `partial`, `failed`, or `cancelled`.
7. Reports are generated as artifacts and later downloaded through authenticated routes.

## Frontend / Backend Boundary

Source paths: `frontend/src/shared/api/endpoints.ts`, `frontend/src/features/auth/api.ts`, `frontend/src/features/audits/api.ts`.

- Frontend does not call the database directly.
- Frontend uses JSON APIs for auth, jobs, job detail, and system status.
- SSE is read directly by `frontend/src/shared/hooks/useSSE.ts`.
- Report download uses a raw `fetch()` to `GET /api/v1/audit/job/{job_id}/report` and opens the returned blob in a new tab.

## Database And Object Storage Boundary

Source paths: `backend/app/models/*`, `backend/app/services/storage.py`, `backend/app/api/routes_storage.py`.

- Relational state lives in the configured SQL database: users, sessions, jobs, findings, logs, artifacts, memberships, policy/security logs, and attestation records.
- Large report and evidence files go through `StorageService.upload_artifact()`.
- If R2/S3-compatible storage is configured, artifact metadata still lands in the database and the file object goes to object storage.
- If object storage is unavailable, files are stored under `workspace/storage`.

## Background Worker Behavior

Source paths: `backend/app/api/routes_audit.py`, `backend/app/workers/celery_app.py`.

- Celery is optional in the current repository.
- `_is_broker_reachable()` probes Redis with a short socket connect.
- If Redis is unavailable, the API logs the fallback and schedules the job in-process using `BackgroundTasks`.
- `backend/app/workers/scheduler.py` exists, but its periodic scan dispatch logic is still placeholder text.

## SSE Streaming Behavior

Source paths: `backend/app/api/routes_sse.py`, `frontend/src/shared/hooks/useSSE.ts`.

- The SSE endpoint is `GET /api/v1/audit/{job_id}/stream`.
- It re-checks job ownership before streaming and again on each polling cycle.
- It emits:
  - `connect` when the stream opens
  - `log` for each new `AgentLog`
  - `complete` when the job reaches a terminal state
  - `error` if the stream breaks
- The backend sends a keepalive comment roughly every 15 seconds when idle.

## Report Generation Flow

Source paths: `backend/app/orchestrator/maestro.py`, `backend/app/services/reporter.py`, `backend/app/services/storage.py`.

1. The reporter phase collects reportable findings from the current `AuditState`.
2. `ReportGenerator.generate_html_report()` renders the report body.
3. `compile_pdf()` uses WeasyPrint when available.
4. If WeasyPrint is unavailable, the code writes an `.html` file plus a simulated placeholder `.pdf`.
5. The report is uploaded through `StorageService.upload_artifact()`, and the job stores an `artifact://...` URL.
6. `GET /api/v1/audit/job/{job_id}/report` resolves the artifact to either a presigned URL, a local file, or an HTML fallback.

## Optional Integrations

Source paths: `backend/app/api/routes_auth.py`, `backend/app/agents/github_mcp.py`, `backend/app/agents/google_agent.py`, `backend/app/services/reporter.py`.

- GitHub OAuth: optional
- Google OAuth: optional
- GitHub/GitMCP issue and PR creation: optional
- Gemini/OpenAI-assisted analysis: optional
- Email sending through SMTP, Resend, or Brevo: optional
- Cloudflare R2 / S3-compatible artifact storage: optional

The code usually degrades gracefully in debug mode and more conservatively in non-debug mode.

## Multi-Tenancy & Resource Scoping

Source paths: `backend/app/middleware/tenant.py`, `backend/app/services/tenant_service.py`, `backend/app/models/tenant.py`, `backend/app/models/compliance.py`.

- **Tenant Isolation**: All jobs, findings, assets, and reports are partitioned at the database layer by a `tenant_id` UUID field.
- **Tenant Resolution**: The `TenantMiddleware` processes incoming requests, checking for the `X-Tenant-Slug` or `X-Tenant-ID` headers. If found, it looks up the tenant in the database, verifies that the tenant is active, and binds the corresponding `tenant_id` to the request's state. If headers are absent, it falls back to resolving the tenant associated with the authenticated user.
- **Scoping Controls**: Access to reports, job statuses, and artifacts is validated at the endpoint level via `verify_tenant_access` checks. Users can only access resources belonging to their own tenant or tenants they have a verified membership with.
- **Plan Enforcement**: The application limits user counts (`max_users`) and object storage allocations (`max_storage_gb`) according to the tenant's configured tier (`free`, `premium`, `enterprise`).

## Platform Scaling & Redundancy

Source paths: `docker-compose.prod.yml`, `infrastructure/terraform/*`.

- **Horizontal Scaling**: In production environments, the application is divided into stateless API containers and background Worker containers. These can scale horizontally based on CPU/Memory load.
- **Load Balancing & Ingress**: Nginx serves as the reverse proxy, load balancer, and SSL termination point. It routes client requests across multiple backend API container replicas (configured as a replicated service with 2 replicas in `docker-compose.prod.yml`).
- **Distributed Job Queue**: Scalability of active security scans is achieved using a Redis-backed Celery cluster. Workers pick up scanning tasks asynchronously, ensuring the API remains highly responsive.
- **High-Availability Database**: A PostgreSQL database (e.g. AWS RDS or Neon DB) with connection pooling handles the relational data, while Redis handles caching, session storage, and the Celery broker queue.
- **Terraform Deployments**: The cloud architecture is fully defined in AWS via Terraform, employing an ALB, a public-private VPC subnet partition, an ECS Fargate cluster with Auto-Scaling Policies, multi-AZ RDS databases, and ElastiCache Redis replication groups.

## Enterprise Security Architecture

Source paths: `backend/app/api/routes_mfa.py`, `backend/app/api/routes_sso.py`, `backend/app/api/routes_pam.py`, `backend/app/api/routes_iam.py`.

- **Federated Authentication (SSO)**: Supports OpenID Connect (OIDC) and SAML 2.0. Domain-level restrictions route logins to corresponding identity providers automatically.
- **Multi-Factor Authentication (MFA)**: Built-in TOTP support requiring verification codes during authentication. Admins are blocked from taking actions unless MFA is enrolled (`MFA_ENFORCE_FOR_ADMINS`).
- **Just-In-Time Privilege Escalation (PAM)**: Implements temporary role escalation to minimize permanent administrative privilege footprint. Grants automatically expire and are pruned.
- **RBAC & ABAC Policies (IAM)**: Fine-grained permissions are assigned to roles, validated by checking resources and actions against policies before allowing request execution. Programmatic API tokens (Service Accounts) use strong hashing.

---
*Documentation last updated: June 29, 2026*
