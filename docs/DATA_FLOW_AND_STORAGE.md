# Data Flow And Storage

This document is based on `backend/app/models/*`, `backend/app/api/routes_*.py`, `backend/app/services/storage.py`, `backend/app/services/reporter.py`, and `backend/app/services/redaction.py`.

## Authentication Data Flow

Source paths: `backend/app/api/routes_auth.py`, `backend/app/services/auth.py`, `backend/app/models/user.py`.

1. Register and login requests arrive with workspace credentials plus privacy-consent metadata.
2. Passwords are hashed with Argon2id in `backend/app/services/auth.py`.
3. A JWT is created with `sub`, `username`, `jti`, and `token_family`.
4. A `UserSession` row is written when a DB session is available.
5. The frontend stores the token, user ID, and workspace name in local storage through `frontend/src/lib/authSession.ts`.
6. Optional OAuth flows store encrypted GitHub tokens on the `users` table.

Stored in database:

- `users`
- `user_sessions`
- `login_failures`
- `security_logs`

## Audit Submission Flow

Source paths: `backend/app/api/routes_audit.py`, `backend/app/schemas/audit_api.py`, `backend/app/orchestrator/runtime.py`.

1. The client submits repo URL, branch, and attestation fields.
2. The route creates an `AuditJob`.
3. The route creates an `AuthorizationAttestation`.
4. The job runs through Celery or `BackgroundTasks`.
5. The runtime initializes `AuditState` and runs the orchestrator graph.

Stored in database:

- `audit_jobs`
- `authorization_attestations`

## Job Persistence

Source paths: `backend/app/models/audit_job.py`, `backend/app/orchestrator/runtime.py`.

`AuditJob` stores:

- job ID
- owner user ID
- tenant ID
- repo URL and branch
- status
- timestamps
- cancellation flags
- `report_pdf_url`
- generic `error_message`

The runtime updates terminal status and timestamps in `_persist_final_job_state()`.

## Finding Persistence

Source paths: `backend/app/orchestrator/maestro.py`, `backend/app/models/audit_job.py`.

`persist_findings()` writes:

- finding metadata
- severity and CVSS fields
- evidence
- remediation
- CWE/OWASP data
- scanner name/mode
- file, line, and route context

Large evidence handling:

- Evidence is redacted before persistence.
- If redacted evidence exceeds 1000 characters, the full redacted text is persisted as a private artifact and the database stores a truncated reference string instead.

## Log Persistence

Source paths: `backend/app/orchestrator/maestro.py`, `backend/app/models/audit_job.py`, `backend/app/api/routes_sse.py`.

- `AgentLog` rows store agent name, level, message, and timestamp.
- SSE streams poll `AgentLog` rows for new entries.
- Security-sensitive route/activity events go to `security_logs`, not `agent_logs`.

## Report Generation

Source paths: `backend/app/orchestrator/maestro.py`, `backend/app/services/reporter.py`, `backend/app/services/storage.py`.

1. The reporter phase renders HTML from reportable findings.
2. The HTML report is stored in `audit_reports`.
3. WeasyPrint is attempted only when a temporary PDF is needed for email delivery.
4. The job stores the authenticated backend report route in `report_pdf_url`.
5. Email delivery is attempted using SMTP, Resend, then Brevo, with a debug-only local email fallback.

## Artifact Storage Behavior

Source paths: `backend/app/services/storage.py`, `backend/app/api/routes_audit.py`.

- `StorageService` writes private overflow artifacts under `workspace/storage` and stores metadata in `artifact_objects`.
- Reports, attack graphs, and HTML snapshots are stored directly in the database.
- Report downloads are served through authenticated backend routes and prefer database HTML content.

## Local Fallback Behavior

Current local fallback paths:

- local artifact storage: `workspace/storage`
- local reports directory: `workspace/reports`
- local debug email output: `workspace/sent_emails`
- local DB files in this repository: `firecrow.db` and `test_firecrow.db`

## What Is Stored In The Database

Verified tables from `backend/app/models/*`:

- `users`
- `login_failures`
- `user_sessions`
- `audit_jobs`
- `findings`
- `agent_logs`
- `audit_artifacts`
- `phase_ledger`
- `security_logs`
- `organizations`
- `memberships`
- `data_processing_records`
- `retention_policies`
- `artifact_objects`
- `compliance_events`
- `privacy_requests`
- `authorization_attestations`
- `secret_redaction_events`

## What Is Stored On Disk

From `backend/app/services/storage.py` and `backend/app/services/reporter.py`:

- temporary report PDFs
- uploaded large evidence text artifacts
- debug email HTML files

## Sensitive Data Handling And Redaction

Source paths: `backend/app/services/redaction.py`, `backend/app/services/security_log.py`, `backend/app/orchestrator/maestro.py`.

- JWTs, GitHub tokens, AWS keys, and generic secrets are redacted before logging or serialization.
- Policy-event logging strips query strings from `href` and `referrer` style fields.
- Secret-history findings replace discovered secret values with `<REDACTED SECRET VALUE>`.
- Large evidence uploads are stored after redaction, not before.

## Known Storage Limitations

- The reporter deletes temporary PDFs after successful email dispatch, so durable report review depends on the database HTML copy, not the transient file.
- Legal-hold behavior exists only for artifact objects, not for every persisted record type.

---
*Documentation last updated: June 08, 2026*
