# Security Model

This document describes engineering controls present in the current repository. It is not a compliance certification statement.

## Authorization-Only Scanning

Source paths: `backend/app/schemas/audit_api.py`, `backend/app/api/routes_audit.py`, `backend/app/orchestrator/scan_plan.py`.

- The submit schema requires `attestation_accepted` and validates that it is `true`.
- The audit route records an `AuthorizationAttestation`.
- Active testing is only enabled when `authorization_scope == "full_active"` and the scan plan allows it.

Current gap:

- The dashboard frontend correctly sends attestation fields required by the backend.

## Auth And Session Model

Source paths: `backend/app/services/auth.py`, `backend/app/api/routes_auth.py`, `backend/app/models/user.py`.

- Access tokens are JWTs signed with `SECRET_KEY`.
- Tokens carry `sub`, `username`, `jti`, `token_family`, issuer, audience, and expiry.
- The backend accepts bearer tokens and the auth cookie.
- Sessions are also persisted in `user_sessions`.
- Logout revokes the active session and token.

## Password Storage

Source paths: `backend/app/services/auth.py`.

- Passwords use Argon2id through `argon2-cffi`.
- Legacy PBKDF2 hashes are still recognized and rehashed on successful login.

## Token Revocation And Lockout

Source paths: `backend/app/services/auth.py`.

- Revoked JTIs are stored in Redis when available.
- Debug mode has an in-memory fallback.
- Login-failure counters use Redis when available or the `login_failures` table otherwise.
- Repeated failures can trigger a lockout.

## Tenant And User Scoping

Source paths: `backend/app/api/audit_queries.py`, `backend/app/api/routes_audit.py`, `backend/app/services/storage.py`, `backend/app/models/compliance.py`.

- Job access is checked by owner user ID, tenant ID, or membership.
- Artifact access is checked through `StorageService.verify_tenant_access()`.
- `list_jobs` can include tenant-visible jobs through memberships.

Current caution:

- Some route comments imply admin-only behavior, but the storage legal-hold route currently enforces tenant access, not a strict admin role check.

## Rate Limiting

Source paths: `backend/app/services/limiter.py`, `backend/app/api/routes_auth.py`, `backend/app/api/routes_audit.py`, `backend/app/main.py`.

- Global default: `100/minute`
- Additional route-level limits:
  - `20/minute` on login and token exchange
  - `10/minute` on registration and audit submission
  - `60/minute` on policy events

## CORS And Security Headers

Source paths: `backend/app/main.py`.

- CORS origins are derived from `FRONTEND_URL`, `CORS_ORIGINS`, and extra localhost origins in debug mode.
- Security headers added on every request:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security`
  - `Content-Security-Policy`
  - `Referrer-Policy: strict-origin-when-cross-origin`

## Request Protection

Source paths: `backend/app/main.py`.

- oversized requests can be rejected with `413`
- malformed `Content-Length` can be rejected with `400`
- every request receives an `X-Request-ID`

## Error Handling And Redaction

Source paths: `backend/app/main.py`, `backend/app/services/redaction.py`, `backend/app/services/security_log.py`.

- token-like values and common secret strings are redacted before logging
- policy-event logging strips sensitive query strings

## Sandbox Isolation

Source paths: `backend/app/services/sandbox.py`, `backend/app/agents/network.py`, `backend/app/agents/attack.py`, `backend/app/agents/exploit.py`.

- sandbox target and scanner containers drop capabilities, use `no-new-privileges`, memory and CPU limits, read-only root FS, and `tmpfs` for `/tmp`
- active scans only run against private, sandbox-like targets
- allowed executables are restricted in `execute_kali_command()`

Current caveat:

- in debug mode the sandbox can simulate Docker behavior instead of proving it

## Scanner Command Restrictions

Source path: `backend/app/services/sandbox.py`.

Allowed executables in standard mode:

- `nmap`
- `sqlmap`
- `nuclei`
- `curl`
- `osv-scanner`
- `trivy`
- `semgrep`

Non-allowlisted commands are rejected outside debug mode.

## Report Download Behavior

Source path: `backend/app/api/routes_audit.py`.

- report downloads require auth
- reports are compiled on-demand from HTML stored in the database

## OAuth And Provider Token Storage

Source paths: `backend/app/api/routes_auth.py`, `backend/app/services/auth.py`.

- GitHub OAuth tokens are stored encrypted in the user record
- Google OAuth currently stores the provider identity, but not a persisted Google access token field
- OAuth callbacks set the auth cookie and redirect with an exchange code instead of putting the token in the URL

## Data Encryption at Rest

- All artifacts (reports, evidence, attack graphs) are stored encrypted at rest in the database (via column-level encryption or application-layer encryption).

## Multi-Factor Authentication (MFA)

Source paths: `backend/app/models/mfa.py`, `backend/app/api/routes_mfa.py`, `backend/app/services/mfa_service.py`, `backend/app/middleware/mfa_enforcement.py`.

- Supports Time-based One-Time Passwords (TOTP) compliant with RFC 6238.
- Enrollment generates a cryptographically random secret and provides a set of one-time recovery codes (hashed before storage).
- MFA verification is required for critical/administrative operations when enabled.
- Session-based admin enforcement: `MFA_ENFORCE_FOR_ADMINS=True` automatically requires any user with an admin/owner role to activate MFA. If they attempt privileged actions (creating providers, approving PAM, deleting users) without MFA active, the request is rejected.
- Compliance checks allow administrators to list all users lacking active MFA and programmatically deactivate administrative accounts failing to comply.

## Single Sign-On (SSO)

Source paths: `backend/app/models/sso.py`, `backend/app/api/routes_sso.py`, `backend/app/services/sso_service.py`.

- Integrates identity federation via OpenID Connect (OIDC) and SAML 2.0.
- OIDC client credentials and tokens (access/refresh tokens) are stored encrypted at rest using the global `ENCRYPTION_KEY`.
- SAML 2.0 implementation leverages XML signature verification using metadata certificates.
- Configurable settings allow per-provider domain constraints (restricting logins to matching email domains), auto-provisioning options, and default role assignment.
- Supports enforcement of MFA downstream from the SSO provider or upstream within the application flow.

## Privileged Access Management (PAM)

Source paths: `backend/app/models/pam.py`, `backend/app/api/routes_pam.py`, `backend/app/services/pam_service.py`.

- Just-In-Time (JIT) role escalation framework. Users request temporary elevation to administrative roles or specific permissions for a limited duration (up to 480 minutes).
- Requests require a detailed business justification and an optional external ticket reference.
- Elevated grants must be approved by an active administrator who has verified MFA.
- Grants automatically expire after the requested duration. A background cleanup worker prunes stale or expired grants.
- Explicit revocation allows administrators to terminate active privileges instantly.
- Comprehensive PAM audit logging logs all escalation requests, approvals, denials, cleanup actions, and resource access.

## Identity & Access Management (IAM) & RBAC

Source paths: `backend/app/models/iam.py`, `backend/app/models/role.py`, `backend/app/api/routes_iam.py`, `backend/app/services/iam_service.py`.

- Implements Role-Based Access Control (RBAC) and fine-grained Attribute-Based Access Control (ABAC) policies.
- Custom IAM Policies define `effect` (allow/deny), `actions`, `resources`, and optional evaluation `conditions`.
- Service Accounts allow programmatic API access via signed, prefix-validated long-lived tokens (`fc_svc_...`). Service account tokens are hashed (SHA-256) prior to database persistence.
- Dormancy auditing detects inactive accounts (no logins for 90 days), triggering automatic deactivation to prevent credential reuse.
- Shared account detection analyzes access logs to identify credentials concurrently utilized across multiple geographic or IP footprints (default threshold of 5 distinct IPs).

## Known Security Gaps And TODOs

- [x] `TelemetryMiddleware` registered in `backend/app/main.py` (fixed).
- The frontend legal and marketing claims have been aligned with the backend guarantees, including a responsive Terms of Service page.

- The current scoring phase uses simple severity mapping, not scanner-native CVSS.

---
*Documentation last updated: June 29, 2026*
