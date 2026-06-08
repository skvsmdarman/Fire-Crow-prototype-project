# API Reference

This reference is derived from `backend/app/main.py`, `backend/app/api/routes_auth.py`, `backend/app/api/routes_audit.py`, `backend/app/api/routes_sse.py`, `backend/app/api/routes_system.py`, and `backend/app/api/routes_storage.py`.

## Auth Endpoints

### `POST /api/v1/auth/exchange`

- Auth required: no
- Request body: `{ code: string }`
- Response: `{ access_token, username, user_id }`
- Errors: `400` for invalid or expired code
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: `frontend/src/features/auth/api.ts` via `exchangeCode()` on the sign-in page

### `GET /api/v1/auth/policy-context`

- Auth required: no
- Request body: none
- Response: privacy version, terms version, and provider availability booleans
- Errors: none in the route itself
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: `frontend/src/features/auth/api.ts`, `frontend/src/app/signup/page.tsx`

### `POST /api/v1/auth/policy-events`

- Auth required: optional
- Request body: `policy`, `event_type`, `policy_version`, optional `source`, `href`, `page_path`, `referrer_path`
- Response: `{ status: "recorded" }`
- Errors: mostly validation errors or auth parsing failures if an invalid token is supplied
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: `frontend/src/lib/policy.ts`, `frontend/src/features/legal/components/PolicyLink.tsx`, `PolicyPageTracker.tsx`

### `POST /api/v1/auth/register`

- Auth required: no
- Request body: `username`, `password`, optional `email`, required privacy consent fields, optional timezone and region
- Response: `{ access_token, token_type, username, user_id }`
- Errors:
  - `400` invalid username/password/privacy version/email collision
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: `frontend/src/app/signup/page.tsx`

### `POST /api/v1/auth/login`

- Auth required: no
- Request body: `username`, `password`, required privacy consent fields, optional timezone and region
- Response: `{ access_token, token_type, username, user_id }`
- Errors:
  - `400` missing fields or unsupported privacy version
  - `401` invalid credentials
  - `429` login lockout or rate limit
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: `frontend/src/features/auth/api.ts` via `loginUser()`

### `POST /api/v1/auth/logout`

- Auth required: yes
- Request body: none
- Response: `{ status: "logged_out" }`
- Errors:
  - `401` unauthenticated
  - `503` token revocation failure
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: `frontend/src/shared/hooks/useAuthSession.ts`

### `GET /api/v1/auth/me`

- Auth required: yes
- Request body: none
- Response: current user/session payload including providers and policy metadata
- Errors:
  - `401` unauthenticated
  - `404` user session could not be resolved
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: `frontend/src/features/auth/api.ts`, `frontend/src/shared/hooks/useAuthSession.ts`

### `GET /api/v1/auth/session`

- Auth required: yes
- Request body: none
- Response: same payload shape as `/auth/me`
- Errors: same as `/auth/me`
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: none confirmed in current frontend

### `GET /api/v1/auth/github`

- Auth required: no
- Request params: `privacy_policy_accepted`, `privacy_policy_version`, optional `timezone`, `region`
- Response: redirect to GitHub OAuth
- Errors:
  - `400` invalid consent/version
  - `503` GitHub OAuth not configured
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: sign-in and sign-up pages build this URL directly

### `GET /api/v1/auth/github/callback`

- Auth required: no
- Request params: `code`, `state`
- Response: redirect to `/signin?code=...` and sets auth cookie
- Errors:
  - `400` invalid OAuth state or upstream exchange failure
  - `503` GitHub OAuth not configured
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: browser redirect target

### `GET /api/v1/auth/google`

- Auth required: no
- Request params: `privacy_policy_accepted`, `privacy_policy_version`, optional `timezone`, `region`
- Response: redirect to Google OAuth
- Errors:
  - `400` invalid consent/version
  - `503` Google OAuth not configured
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: sign-in and sign-up pages build this URL directly

### `GET /api/v1/auth/google/callback`

- Auth required: no
- Request params: `code`, `state`
- Response: redirect to `/signin?code=...` and sets auth cookie
- Errors:
  - `400` invalid OAuth state or upstream exchange failure
  - `503` Google OAuth not configured
- Source: `backend/app/api/routes_auth.py`
- Frontend caller: browser redirect target

## Audit Endpoints

### `POST /api/v1/audit/submit`

- Auth required: yes
- Request body:
  - `repo_url` required, must match GitHub HTTPS pattern
  - `repo_branch` optional, defaults to `main`
  - `attestation_accepted` required in practice because validation rejects `false`
  - `authorization_scope` optional string, defaults to `authorized_representative`
- Response: `JobResponse`
- Errors:
  - `401` unauthenticated
  - `422` payload validation failure
  - `429` active job limit reached
- Source: `backend/app/api/routes_audit.py`, `backend/app/schemas/audit_api.py`
- Frontend caller: intended caller is `frontend/src/features/audits/api.ts`, but the current frontend does not send the attestation fields required by the schema

### `GET /api/v1/audit/jobs`

- Auth required: yes
- Request body: none
- Response: list of `JobResponse`
- Errors: `401`
- Source: `backend/app/api/routes_audit.py`
- Frontend caller: `frontend/src/features/audits/api.ts`

### `GET /api/v1/audit/job/{job_id}`

- Auth required: yes
- Request body: none
- Response: `JobDetailResponse` with job plus findings
- Errors:
  - `401` unauthenticated
  - `404` job not found or not accessible
- Source: `backend/app/api/routes_audit.py`, `backend/app/api/audit_queries.py`
- Frontend caller: `frontend/src/features/audits/api.ts`

### `DELETE /api/v1/audit/job/{job_id}`

- Auth required: yes
- Request body: none
- Response: cancellation acknowledgement
- Errors:
  - `400` job already terminal
  - `401` unauthenticated
  - `404` job not found or not accessible
- Source: `backend/app/api/routes_audit.py`
- Frontend caller: `frontend/src/features/audits/api.ts`

### `GET /api/v1/audit/job/{job_id}/report`

- Auth required: yes
- Request body: none
- Response:
  - HTML content served directly from the database (`audit_reports` table) or compiled as HTML response.
- Errors:
  - `400` unsafe path
  - `401` unauthenticated
  - `404` report missing
  - `500` storage retrieval failure
- Source: `backend/app/api/routes_audit.py`
- Frontend caller: `frontend/src/app/dashboard/page.tsx` via `openReport()`

## SSE Endpoint

### `GET /api/v1/audit/{job_id}/stream`

- Auth required: yes
- Request body: none
- Response: `text/event-stream`
- Events:
  - `connect`
  - `log`
  - `complete`
  - `error`
- Errors:
  - initial `404` if the job is not owned by the user
  - stream-side `error` event on interruption
- Source: `backend/app/api/routes_sse.py`
- Frontend caller: `frontend/src/shared/hooks/useSSE.ts`

## System Endpoint

### `GET /api/v1/system/status`

- Auth required: yes
- Request body: none
- Response:
  - always: API/database/readiness status, current-user job and finding counts, legal versions, agent list
  - admin-like roles only: `debug`, `sandbox_mode`, and `integrations`
- Errors:
  - `401` unauthenticated
- Source: `backend/app/api/routes_system.py`
- Frontend caller: `frontend/src/features/audits/api.ts`

## Health Endpoints

### `GET /health`

- Auth required: no
- Response: `{ status: "up" | "degraded", database: "connected" | "unavailable" }`
- Source: `backend/app/main.py`
- Frontend caller: none confirmed

### `GET /health/live`

- Auth required: no
- Response: `{ status: "live" }`
- Source: `backend/app/main.py`

### `GET /health/ready`

- Auth required: no
- Response:
  - `200` with `{ status: "ready" }` if DB and Redis probes succeed
  - `503` with degraded payload otherwise
- Source: `backend/app/main.py`

### `GET /health/deep`

- Auth required: no
- Response:
  - `200` or `503`
  - includes database, local storage, and object storage states
- Source: `backend/app/main.py`

## Additional Storage Endpoints

These routes exist in the current backend, even though they are not used by the current frontend.

### `GET /api/v1/storage/artifacts/{artifact_id}/download`

- Auth required: yes
- Response: authenticated file download through `StorageService`
- Source: `backend/app/api/routes_storage.py`

### `POST /api/v1/storage/artifacts/{artifact_id}/legal-hold`

- Auth required: yes
- Request param: `hold` boolean query parameter
- Response: legal-hold status payload
- Source: `backend/app/api/routes_storage.py`

Current caution: the route comment says "Admin/scoped," but the access check in `StorageService.verify_tenant_access()` is tenant/membership based and not explicitly admin-only.

## Chat Endpoints

### `POST /api/v1/chat/ask`

- Auth required: yes
- Request body: `{ job_id: string, message: string }`
- Response: `{ response: string, answer: string }` containing the AI assistant's reply.
- Errors:
  - `401` unauthenticated
  - `404` job not found
  - `503` Chat assistant is disabled (LLM feature flag not enabled)
- Source: `backend/app/api/routes_chat.py`

## Leaderboard Endpoints

### `GET /api/v1/leaderboard`

- Auth required: yes
- Request body: none
- Response: Array of objects representing the top 10 finished scan jobs by security score. Each object contains `repo_url`, `score`, `security_score`, `completed_at`, `finished_at`, and `critical_count`.
- Errors:
  - `401` unauthenticated
- Source: `backend/app/api/routes_leaderboard.py`

## Push Notification Endpoints

### `GET /api/v1/push/vapid-public-key`

- Auth required: no
- Request body: none
- Response: `{ public_key: string }`
- Errors:
  - `500` VAPID keys not generated
- Source: `backend/app/api/routes_push.py`

### `POST /api/v1/push/subscribe`

- Auth required: yes
- Request body: `{ endpoint: string, p256dh: string, auth: string }`
- Response: `{ status: "subscribed" }`
- Errors:
  - `401` unauthenticated
- Source: `backend/app/api/routes_push.py`

## Additional Graph & Insight Endpoints

### `GET /api/v1/audit/job/{job_id}/graph`

- Auth required: yes
- Request body: none
- Response: JSON object representing the node-edge correlation matrix of the attack graph.
- Errors:
  - `401` unauthenticated
  - `404` job not found, or attack graph not generated yet
- Source: `backend/app/api/routes_audit.py`

### `GET /api/v1/audit/job/{job_id}/insight`

- Auth required: yes
- Request body: none
- Response: `{ insight: string, enabled: boolean }` where `insight` is a short summary of findings (max 15 words) if `LLM_DASHBOARD_INSIGHT` is enabled.
- Errors:
  - `401` unauthenticated
  - `404` job not found
- Source: `backend/app/api/routes_audit.py`

---
*Documentation last updated: June 08, 2026*
