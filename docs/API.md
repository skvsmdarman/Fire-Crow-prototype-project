# Historical Note

Prefer `docs/API_REFERENCE.md` for the current route documentation tied to the present codebase. This file is older design/reference material.

# Fire Crow API Specification (The Contract)

This document contains the strict contract definitions for all Fire Crow backend REST endpoints and event streams. Both frontend and backend components must conform to these definitions.

---

## 1. Global Headers & Security

Except for public authentication endpoints, API clients should send a Bearer token. Browser OAuth sessions may instead use the secure HTTP-only `fc_access_token` cookie set by the callback handler.

```http
Authorization: Bearer <token>
Content-Type: application/json
Accept: application/json
```

---

## 2. Authentication Router (`/api/v1/auth`)

### 2.1 Register Workspace User
Create a new database-backed user/workspace.

* **Route**: `POST /api/v1/auth/register`
* **Content-Type**: `application/json`
* **Request Payload**:
  ```json
  {
    "username": "my-secure-workspace",
    "password": "strongpassword123",
    "email": "security@mycompany.com",
    "privacy_policy_accepted": true,
    "privacy_policy_version": "2026-06-06"
  }
  ```
  *Note: `username`, `password`, `privacy_policy_accepted`, and `privacy_policy_version` are required. `email` is optional. Password must be at least 8 characters.*

* **Success Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "username": "my-secure-workspace",
    "user_id": "8df52466-6b50-48c2-8de3-b37cb31ad1a5"
  }
  ```
* **Error Response (400 Bad Request)**:
  ```json
  {
    "detail": "Username is already registered"
  }
  ```

### 2.2 Login / Session Token Initiation
Authenticate workspace credentials and receive a JWT token. 

* **Route**: `POST /api/v1/auth/login`
* **Content-Type**: `application/json`
* **Request Payload**:
  ```json
  {
    "username": "my-secure-workspace",
    "password": "strongpassword123",
    "privacy_policy_accepted": true,
    "privacy_policy_version": "2026-06-06"
  }
  ```
  *Note: `username`, `password`, and current Privacy Policy consent fields are required.*

* **Success Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "username": "my-secure-workspace",
    "user_id": "8df52466-6b50-48c2-8de3-b37cb31ad1a5"
  }
  ```
* **Error Response (401 Unauthorized)**:
  ```json
  {
    "detail": "Invalid workspace name or password"
  }
  ```

### 2.3 Get Authenticated Profile
Retrieve current session tenant details. Used to validate token expiration on load.

* **Route**: `GET /api/v1/auth/me`
* **Headers**: `Authorization: Bearer <token>` or `fc_access_token` cookie
* **Success Response (200 OK)**:
  ```json
  {
    "user_id": "8df52466-6b50-48c2-8de3-b37cb31ad1a5",
    "username": "my-secure-workspace",
    "email": "security@mycompany.com",
    "role": "security_engineer"
  }
  ```
* **Error Response (401 Unauthorized)**:
  ```json
  {
    "detail": "Could not validate credentials"
  }
  ```

### 2.4 GitHub OAuth Initiation
Start GitHub OAuth flow. If GitHub OAuth credentials are not configured, the endpoint returns `503 Service Unavailable`.

* **Route**: `GET /api/v1/auth/github?state=some_random_state`
* **Query Parameters**:
  * `state` (optional string)
  * `privacy_policy_accepted` (required boolean)
  * `privacy_policy_version` (required string)
* **Success Response (302 Redirect)**: Redirects browser to `https://github.com/login/oauth/authorize`

### 2.5 GitHub Callback Handler
Receives GitHub authorization code and returns user profile session redirect.

* **Route**: `GET /api/v1/auth/github/callback`
* **Query Parameters**:
  * `code` (required string)
  * `state` (optional string)
  * `mock_username` (optional string, sandbox mode only)
  * `mock_email` (optional string, sandbox mode only)
  * `mock_id` (optional string, sandbox mode only)
* **Success Response (302 Redirect)**:
  Redirects to: `{FRONTEND_URL}/signin` and sets `fc_access_token` as an HTTP-only cookie. JWTs are never placed in redirect URLs.

### 2.6 Session Lookup
Return the authenticated browser/API session profile.

* **Route**: `GET /api/v1/auth/session`
* **Headers**: `Authorization: Bearer <token>` or `fc_access_token` cookie

### 2.7 Google OAuth Initiation
Start Google OpenID flow. If Google OAuth credentials are not configured, the endpoint returns `503 Service Unavailable`.

* **Route**: `GET /api/v1/auth/google?state=some_random_state`
* **Query Parameters**:
  * `state` (optional string)
  * `privacy_policy_accepted` (required boolean)
  * `privacy_policy_version` (required string)
* **Success Response (302 Redirect)**: Redirects browser to `https://accounts.google.com/o/oauth2/v2/auth`

### 2.8 Google Callback Handler
Receives Google authorization code and returns user profile session redirect.

* **Route**: `GET /api/v1/auth/google/callback`
* **Query Parameters**:
  * `code` (required string)
  * `state` (optional string)
  * `mock_username` (optional string, sandbox mode only)
  * `mock_email` (optional string, sandbox mode only)
  * `mock_id` (optional string, sandbox mode only)
* **Success Response (302 Redirect)**:
  Redirects to: `{FRONTEND_URL}/signin` and sets `fc_access_token` as an HTTP-only cookie. JWTs are never placed in redirect URLs.

---

## 3. Security Auditing Router (`/api/v1/audit`)

### 3.1 Submit Audit Job
Triggers an autonomous security audit of a public GitHub repository.

* **Route**: `POST /api/v1/audit/submit`
* **Headers**: `Authorization: Bearer <token>`, `Content-Type: application/json`
* **Request Payload**:
  ```json
  {
    "repo_url": "https://github.com/octocat/hello-world",
    "repo_branch": "main"
  }
  ```
  *Note: `repo_url` must match `^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+(\.git)?$`*

* **Success Response (201 Created)**:
  ```json
  {
    "id": "job_e79c2a38-4e1b-4cd3-89bd-06db8cf622eb",
    "user_id": "8df52466-6b50-48c2-8de3-b37cb31ad1a5",
    "repo_url": "https://github.com/octocat/hello-world",
    "repo_branch": "main",
    "status": "queued",
    "created_at": "2026-06-06T00:00:00Z",
    "finished_at": null,
    "cancel_requested": false,
    "cancel_requested_at": null,
    "report_pdf_url": null,
    "error_message": null
  }
  ```
* **Error Response (422 Unprocessable Entity)**:
  ```json
  {
    "detail": [
      {
        "loc": ["body", "repo_url"],
        "msg": "Only public GitHub HTTPS URLs are supported.",
        "type": "value_error"
      }
    ]
  }
  ```

### 3.2 List Workspace Jobs
Returns all jobs triggered under the current authenticated session.

* **Route**: `GET /api/v1/audit/jobs`
* **Headers**: `Authorization: Bearer <token>`
* **Success Response (200 OK)**:
  ```json
  [
    {
      "id": "job_e79c2a38-4e1b-4cd3-89bd-06db8cf622eb",
      "user_id": "8df52466-6b50-48c2-8de3-b37cb31ad1a5",
      "repo_url": "https://github.com/octocat/hello-world",
      "repo_branch": "main",
      "status": "completed",
      "created_at": "2026-06-06T00:00:00Z",
      "finished_at": "2026-06-06T00:05:32Z",
      "cancel_requested": false,
      "cancel_requested_at": null,
      "report_pdf_url": "https://r2.firecrow.dev/reports/job_e79c2a38.pdf",
      "error_message": null
    }
  ]
  ```

### 3.3 Get Job Detail & Findings
Retrieve full data of a job, including structured code findings.

* **Route**: `GET /api/v1/audit/job/{job_id}`
* **Headers**: `Authorization: Bearer <token>`
* **Success Response (200 OK)**:
  ```json
  {
    "job": {
      "id": "job_e79c2a38-4e1b-4cd3-89bd-06db8cf622eb",
      "user_id": "8df52466-6b50-48c2-8de3-b37cb31ad1a5",
      "repo_url": "https://github.com/octocat/hello-world",
      "repo_branch": "main",
      "status": "completed",
      "created_at": "2026-06-06T00:00:00Z",
      "finished_at": "2026-06-06T00:05:32Z",
      "cancel_requested": false,
      "cancel_requested_at": null,
      "report_pdf_url": "https://r2.firecrow.dev/reports/job_e79c2a38.pdf",
      "error_message": null
    },
    "findings": [
      {
        "id": "fnd_8b2cd190",
        "agent_source": "SAST",
        "title": "Hardcoded JWT Signing Key",
        "description": "A plaintext cryptographic key signature was identified inside the source code configuration file.",
        "severity": "critical",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "evidence": "scanner_name=regex-sast; scanner_mode=regex; confidence=medium\nfile=backend/app/config.py; line=16; signature=Generic Password / Key Leak; redacted_fingerprint=sha256:3c0f5a7b1e2d",
        "remediation": "Move all sensitive credential settings to env parameters and load dynamically."
      }
    ]
  }
  ```
* **Error Response (404 Not Found)**:
  ```json
  {
    "detail": "Job not found"
  }
  ```

### 3.4 Request Job Cancellation
Signals the running execution queue to terminate worker actions and release containers.

* **Route**: `DELETE /api/v1/audit/job/{job_id}`
* **Headers**: `Authorization: Bearer <token>`
* **Success Response (200 OK)**:
  ```json
  {
    "message": "Job cancellation request recorded successfully",
    "job_id": "job_e79c2a38-4e1b-4cd3-89bd-06db8cf622eb"
  }
  ```
* **Error Response (400 Bad Request)**:
  ```json
  {
    "detail": "Job cannot be cancelled in status completed"
  }
  ```

### 3.5 Download PDF Report
Downloads the compiled executive PDF audit report. 

* **Route**: `GET /api/v1/audit/job/{job_id}/report`
* **Headers**: `Authorization: Bearer <token>`
* **Success Response**: Returns a local binary file (`application/pdf`) or redirects only to the configured Cloudflare R2 HTTPS host.
* **Error Response (400 Bad Request)**: Returned when a stored report URL is not a safe local report path or configured report-storage URL.

---

## 4. Live Events Server-Sent Stream (`/api/v1/audit`)

### 4.1 Live Stream Job Events
Establishes a continuous SSE streaming channel to push agent execution logs and pipeline status.

* **Route**: `GET /api/v1/audit/{job_id}/stream`
* **Headers**: 
  * `Authorization: Bearer <token>`
  * `Accept: text/event-stream`
* **Success Response Stream**:

  * **Connection Initiated (`event: connect`)**:
    ```data
    event: connect
    data: {"status": "connected", "job_id": "job_e79c2a38-4e1b-4cd3-89bd-06db8cf622eb"}
    ```
  
  * **Log Received (`event: log`)**:
    ```data
    event: log
    data: {"id": 12, "agent_name": "SAST", "log_level": "INFO", "message": "Analyzing python configuration variables...", "timestamp": "2026-06-06T00:01:15Z"}
    ```
  
  * **Job Finalized (`event: complete`)**:
    ```data
    event: complete
    data: {"status": "completed", "finished_at": "2026-06-06T00:05:32Z", "cancel_requested": false, "cancel_requested_at": null, "report_pdf_url": "https://r2.firecrow.dev/reports/job_e79c2a38.pdf", "error_message": null}
    ```

---

## 5. System Management Router (`/api/v1/system`)

### 5.1 System Health Status
Retrieves current system details, database check, integrations and ready security nodes status.

* **Route**: `GET /api/v1/system/status`
* **Headers**: `Authorization: Bearer <token>`
* **Success Response (200 OK)**:
  ```json
  {
    "api": "online",
    "database": "connected",
    "debug": true,
    "sandbox_mode": "docker",
    "stats": {
      "jobs": 3,
      "findings": 12
    },
    "integrations": {
      "github_oauth": true,
      "redis": true,
      "report_storage": true,
      "email": true,
      "ai_models": true
    },
    "agents": [
      {"name": "MAESTRO", "role": "Orchestration", "status": "ready"},
      {"name": "RECON", "role": "Repository clone and stack detection", "status": "ready"},
      {"name": "SAST", "role": "Secrets and unsafe code analysis", "status": "ready"},
      {"name": "SANDBOX", "role": "Kali runtime provisioning", "status": "ready"},
      {"name": "NETWORK", "role": "Port and service discovery", "status": "ready"},
      {"name": "ATTACK", "role": "Automated active scanning", "status": "ready"},
      {"name": "EXPLOIT", "role": "Proof generation", "status": "ready"},
      {"name": "SCORING", "role": "CVSS prioritization", "status": "ready"},
      {"name": "REPORTER", "role": "Report generation", "status": "ready"},
      {"name": "GITHUB_MCP", "role": "GitMCP issue and PR generation", "status": "ready"}
    ]
  }
  ```
  *Note: `stats` are scoped to the authenticated workspace. The public `/health` endpoint remains available for uptime checks.*
