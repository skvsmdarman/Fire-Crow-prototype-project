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

## Multi-Factor Authentication (MFA) Endpoints

### `POST /api/v1/mfa/enroll`
- Auth required: yes
- Rate limit: `5/minute`
- Response: `{ secret: string, uri: string, recovery_codes: list[str] }`
- Source: `backend/app/api/routes_mfa.py`

### `POST /api/v1/mfa/activate`
- Auth required: yes
- Rate limit: `10/minute`
- Request body: `{ token: string }`
- Response: `{ status: "activated", activated_at: string }`
- Source: `backend/app/api/routes_mfa.py`

### `POST /api/v1/mfa/verify`
- Auth required: yes
- Rate limit: `10/minute`
- Request body: `{ token: string }`
- Response: `{ verified: boolean }`
- Source: `backend/app/api/routes_mfa.py`

### `POST /api/v1/mfa/recovery`
- Auth required: yes
- Rate limit: `3/minute`
- Request body: `{ code: string }`
- Response: `{ verified: boolean }`
- Source: `backend/app/api/routes_mfa.py`

### `POST /api/v1/mfa/regenerate-codes`
- Auth required: yes
- Rate limit: `2/minute`
- Response: `{ recovery_codes: list[str] }`
- Source: `backend/app/api/routes_mfa.py`

### `POST /api/v1/mfa/disable`
- Auth required: yes
- Rate limit: `3/minute`
- Response: `{ status: "mfa_disabled" }`
- Source: `backend/app/api/routes_mfa.py`

### `GET /api/v1/mfa/status`
- Auth required: yes
- Response: `{ is_active: boolean, method: string, created_at: string, last_verified_at: string, has_recovery_codes: boolean }`
- Source: `backend/app/api/routes_mfa.py`

### `GET /api/v1/mfa/admin/compliance`
- Auth required: yes (admin-only)
- Response: `{ requires_mfa: boolean, users_without_mfa: list[dict] }`
- Source: `backend/app/api/routes_mfa.py`

### `POST /api/v1/mfa/admin/enforce`
- Auth required: yes (admin-only)
- Response: `{ status: "enforced", deactivated_count: integer }`
- Source: `backend/app/api/routes_mfa.py`

## Single Sign-On (SSO) Endpoints

### `GET /api/v1/sso/providers`
- Auth required: yes (admin-only)
- Response: `{ providers: list[dict] }`
- Source: `backend/app/api/routes_sso.py`

### `POST /api/v1/sso/providers`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: `{ name: string, provider_type: string, issuer_url?: string, client_id?: string, client_secret?: string, authorization_url?: string, token_url?: string, userinfo_url?: string, jwks_url?: string, certificate?: string, attribute_mapping?: dict, domains?: list[str], enforce_mfa?: boolean, auto_provision?: boolean, default_role_id?: string }`
- Response: SSO provider configuration dictionary
- Source: `backend/app/api/routes_sso.py`

### `GET /api/v1/sso/providers/{provider_id}`
- Auth required: yes (admin-only)
- Response: SSO provider configuration dictionary
- Source: `backend/app/api/routes_sso.py`

### `PUT /api/v1/sso/providers/{provider_id}`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: SSO provider configuration updates
- Response: updated SSO provider configuration
- Source: `backend/app/api/routes_sso.py`

### `DELETE /api/v1/sso/providers/{provider_id}`
- Auth required: yes (admin-only, MFA verified if required)
- Response: `{ status: "deleted" }`
- Source: `backend/app/api/routes_sso.py`

### `GET /api/v1/sso/oidc/{provider_id}/login`
- Auth required: no
- Response: 302 Redirect to identity provider authorize endpoint
- Source: `backend/app/api/routes_sso.py`

### `GET /api/v1/sso/oidc/callback`
- Auth required: no
- Request params: `code`, `state`
- Response: 302 Redirect to `/signin?code=...` (sets auth cookie)
- Source: `backend/app/api/routes_sso.py`

### `POST /api/v1/sso/saml/{provider_id}/login`
- Auth required: no
- Response: 302 Redirect to SAML Identity Provider login URL
- Source: `backend/app/api/routes_sso.py`

### `POST /api/v1/sso/saml/{provider_id}/callback`
- Auth required: no
- Request body: `SAMLResponse` (form-data)
- Response: 302 Redirect to `/signin?code=...` (sets auth cookie)
- Source: `backend/app/api/routes_sso.py`

## Privileged Access Management (PAM) Endpoints

### `POST /api/v1/pam/requests`
- Auth required: yes
- Rate limit: `10/minute`
- Request body: `{ role_name: string, permission: string, reason: string, requested_duration_minutes: integer, ticket_ref?: string }`
- Response: privilege request status details
- Source: `backend/app/api/routes_pam.py`

### `GET /api/v1/pam/requests`
- Auth required: yes
- Response: list of pending privilege requests (all pending requests if admin, user-scoped pending requests if regular user)
- Source: `backend/app/api/routes_pam.py`

### `GET /api/v1/pam/requests/pending`
- Auth required: yes (admin-only)
- Response: `{ requests: list[dict] }` containing all pending PAM requests
- Source: `backend/app/api/routes_pam.py`

### `POST /api/v1/pam/requests/{request_id}/approve`
- Auth required: yes (admin-only, MFA verified if required)
- Rate limit: `20/minute`
- Request body: `{ duration_minutes?: integer }`
- Response: privilege access grant details
- Source: `backend/app/api/routes_pam.py`

### `POST /api/v1/pam/requests/{request_id}/deny`
- Auth required: yes (admin-only)
- Request body: `{ reason?: string }`
- Response: privilege request status details (denied status)
- Source: `backend/app/api/routes_pam.py`

### `POST /api/v1/pam/requests/{request_id}/cancel`
- Auth required: yes
- Response: privilege request status details (cancelled status)
- Source: `backend/app/api/routes_pam.py`

### `GET /api/v1/pam/grants`
- Auth required: yes
- Response: `{ grants: list[dict] }` (all active grants if admin, user-scoped active grants if regular user)
- Source: `backend/app/api/routes_pam.py`

### `POST /api/v1/pam/grants/revoke`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: `{ grant_id: string }`
- Response: `{ status: "revoked" }`
- Source: `backend/app/api/routes_pam.py`

### `POST /api/v1/pam/cleanup`
- Auth required: yes (admin-only)
- Response: `{ expired_grants_cleaned: integer }`
- Source: `backend/app/api/routes_pam.py`

### `GET /api/v1/pam/check/{permission}`
- Auth required: yes
- Response: `{ permission: string, granted: boolean }`
- Source: `backend/app/api/routes_pam.py`

## Identity & Access Management (IAM) Endpoints

### `GET /api/v1/iam/policies`
- Auth required: yes (admin-only)
- Response: `{ policies: list[dict] }`
- Source: `backend/app/api/routes_iam.py`

### `POST /api/v1/iam/policies`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: `{ name: string, effect: string, actions: list[str], resources: list[str], description?: string, conditions?: string, priority?: integer }`
- Response: IAM policy dictionary details
- Source: `backend/app/api/routes_iam.py`

### `DELETE /api/v1/iam/policies/{policy_id}`
- Auth required: yes (admin-only, MFA verified if required)
- Response: `{ status: "deleted" }`
- Source: `backend/app/api/routes_iam.py`

### `GET /api/v1/iam/role-permissions/{role_id}`
- Auth required: yes (admin-only)
- Response: `{ role_id: string, permissions: list[dict] }`
- Source: `backend/app/api/routes_iam.py`

### `POST /api/v1/iam/role-permissions`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: `{ role_id: string, permission: string, resource_pattern?: string }`
- Response: role permission assignment details
- Source: `backend/app/api/routes_iam.py`

### `DELETE /api/v1/iam/role-permissions/{permission_id}`
- Auth required: yes (admin-only, MFA verified if required)
- Response: `{ status: "deleted" }`
- Source: `backend/app/api/routes_iam.py`

### `POST /api/v1/iam/users/deactivate`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: `{ user_id: string, reason?: string }`
- Response: `{ status: "deactivated" }`
- Source: `backend/app/api/routes_iam.py`

### `POST /api/v1/iam/users/reactivate`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: `{ user_id: string }`
- Response: `{ status: "reactivated" }`
- Source: `backend/app/api/routes_iam.py`

### `DELETE /api/v1/iam/users/{target_user_id}`
- Auth required: yes (admin-only, MFA verified if required)
- Response: `{ status: "permanently_deleted" }`
- Source: `backend/app/api/routes_iam.py`

### `GET /api/v1/iam/audit/dormant`
- Auth required: yes (admin-only)
- Query params: `days` (default 90)
- Response: `{ dormant_users: list[dict], threshold_days: integer }`
- Source: `backend/app/api/routes_iam.py`

### `GET /api/v1/iam/audit/shared-accounts`
- Auth required: yes (admin-only)
- Query params: `threshold_ips` (default 5)
- Response: `{ suspected_shared_accounts: list[dict], threshold_ips: integer }`
- Source: `backend/app/api/routes_iam.py`

### `POST /api/v1/iam/cleanup`
- Auth required: yes (admin-only, MFA verified if required)
- Query params: `dormant_days` (default 90)
- Response: `{ cleanup_stats: dict }`
- Source: `backend/app/api/routes_iam.py`

### `POST /api/v1/iam/service-accounts`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: `{ name: string, permissions: list[str], description?: string, expires_in_days?: integer }`
- Response: Service Account credentials (including generated plain-text token value `fc_svc_...` returned exactly once)
- Source: `backend/app/api/routes_iam.py`

### `POST /api/v1/iam/service-accounts/{account_id}/revoke`
- Auth required: yes (admin-only)
- Response: `{ status: "revoked" }`
- Source: `backend/app/api/routes_iam.py`

### `GET /api/v1/iam/check/{permission}`
- Auth required: yes
- Query params: `resource` (default "*")
- Response: `{ permission: string, resource: string, granted: boolean }`
- Source: `backend/app/api/routes_iam.py`

## Multi-Tenancy Endpoints

### `GET /api/v1/tenants/`
- Auth required: yes (admin-only)
- Response: `{ tenants: list[dict] }`
- Source: `backend/app/api/routes_tenant.py`

### `POST /api/v1/tenants/`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: `{ name: string, slug: string, domain?: string, plan?: string, max_users?: integer, max_storage_gb?: integer }`
- Response: tenant details
- Source: `backend/app/api/routes_tenant.py`

### `GET /api/v1/tenants/me`
- Auth required: yes
- Response: current tenant details resolved from headers (`X-Tenant-Slug` or `X-Tenant-ID`) or current user association
- Source: `backend/app/api/routes_tenant.py`

### `GET /api/v1/tenants/{tenant_id}`
- Auth required: yes (admin-only)
- Response: tenant details
- Source: `backend/app/api/routes_tenant.py`

### `GET /api/v1/tenants/slug/{slug}`
- Auth required: yes (admin-only)
- Response: tenant details
- Source: `backend/app/api/routes_tenant.py`

### `PUT /api/v1/tenants/{tenant_id}`
- Auth required: yes (admin-only, MFA verified if required)
- Request body: tenant settings updates
- Response: updated tenant details
- Source: `backend/app/api/routes_tenant.py`

### `DELETE /api/v1/tenants/{tenant_id}`
- Auth required: yes (admin-only, MFA verified if required)
- Response: `{ status: "deactivated" }`
- Source: `backend/app/api/routes_tenant.py`

### `GET /api/v1/tenants/{tenant_id}/stats`
- Auth required: yes (admin-only)
- Response: tenant usage stats (user count, active jobs count, total jobs, plan constraints)
- Source: `backend/app/api/routes_tenant.py`

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
*Documentation last updated: June 29, 2026*
