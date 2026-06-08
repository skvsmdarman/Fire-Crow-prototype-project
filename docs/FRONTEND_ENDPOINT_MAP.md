# Historical Note

Prefer `docs/FRONTEND_STRUCTURE.md` and `docs/API_REFERENCE.md` for the current frontend/backend mapping. This file is older design/reference material.

# Frontend Endpoint Map

This document maps all the frontend pages and components to the backend API endpoints. It defines the HTTP methods, payloads, expected response shapes, authentication requirements, UI state handling, and any changes needed during the refactoring process.

---

## 1. Authentication & Policies

### `GET /api/v1/auth/policy-context`
*   **Used by**: `signin/page.tsx`
*   **Method**: `GET`
*   **Auth Required**: No (Public)
*   **Request Body**: None
*   **Response Shape**:
    ```json
    {
      "privacy_policy_version": "string",
      "terms_version": "string",
      "providers": {
        "github": boolean,
        "google": boolean,
        "password": boolean
      }
    }
    ```
*   **Loading State**: `loadingContext === true` (shows fallback policy version and default forms or spinner).
*   **Empty State**: N/A
*   **Error State**: Fallback to hardcoded policy versions (`2026-06-06`) and standard password login.
*   **Backend Status**: Exists
*   **Required Frontend Change**: Refactor fetching logic into `features/auth/hooks.ts` and ensure it uses the central API client.

### `POST /api/v1/auth/policy-events`
*   **Used by**: `components/PolicyLink.tsx`, `PolicyPageTracker.tsx` (via `lib/policy.ts`)
*   **Method**: `POST`
*   **Auth Required**: Optional (will attach Authorization header if a token is present in localStorage)
*   **Request Body**:
    ```json
    {
      "policy": "terms" | "privacy_policy",
      "event_type": "link_click" | "page_view",
      "policy_version": "string",
      "source": "string" (optional),
      "href": "string" (optional),
      "page_path": "string" (optional),
      "referrer_path": "string" (optional)
    }
    ```
*   **Response Shape**:
    ```json
    {
      "status": "recorded"
    }
    ```
*   **Loading State**: None (fires in background)
*   **Empty State**: N/A
*   **Error State**: Fails silently (logged to console, does not interrupt navigation)
*   **Backend Status**: Exists
*   **Required Frontend Change**: Move utility into `features/legal/api.ts` and use the central API client.

### `POST /api/v1/auth/login`
*   **Used by**: `signin/page.tsx`
*   **Method**: `POST`
*   **Auth Required**: No (Public)
*   **Request Body**:
    ```json
    {
      "username": "string",
      "password": "string",
      "privacy_policy_accepted": true,
      "privacy_policy_version": "string",
      "timezone": "string" (optional),
      "region": "string" (optional)
    }
    ```
*   **Response Shape**:
    ```json
    {
      "access_token": "string",
      "token_type": "string",
      "username": "string",
      "user_id": "string"
    }
    ```
*   **Loading State**: `loading === true` (disables form submit, shows loading spinner in button)
*   **Empty State**: N/A
*   **Error State**: Set `error` message string, displayed in UI with red warning panel.
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/auth/api.ts` and integrate with central session state hook.

### `POST /api/v1/auth/exchange`
*   **Used by**: `signin/page.tsx` (handles OAuth callback)
*   **Method**: `POST`
*   **Auth Required**: No (Public)
*   **Request Body**:
    ```json
    {
      "code": "string"
    }
    ```
*   **Response Shape**:
    ```json
    {
      "access_token": "string",
      "username": "string",
      "user_id": "string"
    }
    ```
*   **Loading State**: Full-screen validation card with spinner
*   **Empty State**: N/A
*   **Error State**: Displayed in UI warning panel with route reset
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/auth/api.ts`.

### `GET /api/v1/auth/github` / `GET /api/v1/auth/google`
*   **Used by**: `signin/page.tsx` (OAuth redirect trigger links)
*   **Method**: `GET` (Navigation redirect)
*   **Auth Required**: No (Public)
*   **Request Body**: None (URL search params query string parameters: `privacy_policy_accepted`, `privacy_policy_version`, `timezone`, `region`)
*   **Response Shape**: Redirects to OAuth provider login page
*   **Loading State**: Browser page load
*   **Empty State**: N/A
*   **Error State**: Redirects back with errors or fails to load provider page.
*   **Backend Status**: Exists
*   **Required Frontend Change**: Centralize OAuth URL construction in `features/auth/utils.ts` or `shared/utils/routes.ts`.

### `GET /api/v1/auth/me`
*   **Used by**: `dashboard/page.tsx` (verifies session token on mount)
*   **Method**: `GET`
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**:
    ```json
    {
      "id": "string",
      "username": "string",
      "email": "string" (optional)
    }
    ```
*   **Loading State**: Shows global console spinner `!authReady`
*   **Empty State**: Redirects to `/signin`
*   **Error State**: Clears stored session, redirects to `/signin`
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/auth/api.ts` and call it as part of session validation inside `shared/hooks/useAuthSession.ts`.

### `POST /api/v1/auth/logout`
*   **Used by**: `dashboard/page.tsx`
*   **Method**: `POST`
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**:
    ```json
    {
      "message": "Logged out successfully"
    }
    ```
*   **Loading State**: Clearing local state
*   **Empty State**: N/A
*   **Error State**: Logged to console, proceeds with clearing local storage and redirecting anyway
*   **Backend Status**: Exists
*   **Required Frontend Change**: Move to `features/auth/api.ts` and centralize in the auth session hook.

---

## 2. Audit Orchestration & SSE

### `POST /api/v1/audit/submit`
*   **Used by**: `dashboard/components/AuditForm.tsx` (triggered from Dashboard UI)
*   **Method**: `POST`
*   **Auth Required**: Yes
*   **Request Body**:
    ```json
    {
      "repo_url": "string",
      "repo_branch": "string"
    }
    ```
*   **Response Shape**:
    ```json
    {
      "id": "string",
      "user_id": "string",
      "repo_url": "string",
      "repo_branch": "string",
      "status": "queued" | "running" | "completed" | "failed" | "cancelled" | "partial",
      "created_at": "string",
      "finished_at": "string" | null,
      "cancel_requested": boolean,
      "cancel_requested_at": "string" | null,
      "report_pdf_url": "string" | null,
      "error_message": "string" | null
    }
    ```
*   **Loading State**: `submitting === true` (blocks intake form button, shows loading toast)
*   **Empty State**: N/A
*   **Error State**: Shown in form error panel
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/audits/api.ts`.

### `GET /api/v1/audit/jobs`
*   **Used by**: `dashboard/page.tsx`, `dashboard/components/JobList.tsx`
*   **Method**: `GET`
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**: `Job[]`
*   **Loading State**: `loadingJobs === true` (spinner on the job list)
*   **Empty State**: "No audit activity is available yet."
*   **Error State**: Standard error messages
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/audits/api.ts`.

### `GET /api/v1/audit/job/{job_id}`
*   **Used by**: `dashboard/page.tsx`
*   **Method**: `GET`
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**:
    ```json
    {
      "job": {
        "id": "string",
        "user_id": "string",
        "repo_url": "string",
        "repo_branch": "string",
        "status": "queued" | "running" | "completed" | "failed" | "cancelled" | "partial",
        "created_at": "string",
        "finished_at": "string" | null,
        "cancel_requested": boolean,
        "cancel_requested_at": "string" | null,
        "report_pdf_url": "string" | null,
        "error_message": "string" | null
      },
      "findings": [
        {
          "id": "string",
          "agent_source": "string",
          "title": "string",
          "description": "string",
          "severity": "critical" | "high" | "medium" | "low" | "info",
          "cvss_score": number | null,
          "cvss_vector": "string" | null,
          "evidence": "string" | null,
          "remediation": "string" | null
        }
      ]
    }
    ```
*   **Loading State**: `loadingDetail === true`
*   **Empty State**: Detail panel empty or showing placeholder text
*   **Error State**: standard toast / error text
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/audits/api.ts` or `features/findings/api.ts`.

### `DELETE /api/v1/audit/job/{job_id}`
*   **Used by**: `dashboard/page.tsx` (cancellation request button)
*   **Method**: `DELETE`
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**:
    ```json
    {
      "message": "Cancellation request processed successfully"
    }
    ```
*   **Loading State**: Toast message triggered
*   **Empty State**: N/A
*   **Error State**: Toast error message
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/audits/api.ts`.

### `GET /api/v1/audit/job/{job_id}/report`
*   **Used by**: `dashboard/page.tsx` (download PDF trigger)
*   **Method**: `GET`
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**: Binary PDF file blob
*   **Loading State**: Toast showing "Retrieving report PDF..."
*   **Empty State**: N/A
*   **Error State**: Set `reportError` string, error toast shown
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/audits/api.ts`.

### `GET /api/v1/audit/{job_id}/stream`
*   **Used by**: `dashboard/page.tsx` / `LogStream.tsx`
*   **Method**: `GET` (Server-Sent Events)
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**: SSE streams of `LogLine` chunks and job update events
    ```json
    // Inside stream:
    {
      "id": number,
      "agent_name": "string",
      "log_level": "string",
      "message": "string",
      "timestamp": "string"
    }
    ```
*   **Loading State**: Green "live logs" indicator badge
*   **Empty State**: Empty console output
*   **Error State**: Display "Log stream disconnected." as a system log row
*   **Backend Status**: Exists
*   **Required Frontend Change**: Centralize in `shared/hooks/useSSE.ts` to manage event listeners, connection closure, keepalive, and UI limits.

---

## 3. System Status

### `GET /api/v1/system/status`
*   **Used by**: `dashboard/page.tsx`
*   **Method**: `GET`
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**:
    ```json
    {
      "api": "online",
      "database": "connected" | "unavailable",
      "readiness": "ready" | "degraded",
      "stats": {
        "jobs": number,
        "findings": number
      },
      "legal": {
        "privacy_policy_version": "string",
        "terms_version": "string"
      },
      "agents": [
        {
          "name": "string",
          "role": "string",
          "status": "ready" | "degraded"
        }
      ],
      "debug": boolean (optional - only returned if user is admin),
      "sandbox_mode": "simulation" | "docker" (optional - only returned if user is admin),
      "integrations": {
        "github_oauth": boolean,
        "google_oauth": boolean,
        "redis": boolean,
        "report_storage": boolean,
        "email": boolean,
        "ai_models": boolean
      } (optional - only returned if user is admin)
    }
    ```
*   **Loading State**: `loadingSystem === true` (refresh spin animation)
*   **Empty State**: "System status has not loaded yet."
*   **Error State**: Shown in red system notice card
*   **Backend Status**: Exists
*   **Required Frontend Change**: Extract to `features/system/api.ts`.

---

## 4. Other Available Endpoints (No current UI usage)

### `GET /api/v1/storage/artifacts/{artifact_id}/download`
*   **Method**: `GET`
*   **Auth Required**: Yes
*   **Request Body**: None
*   **Response Shape**: File download stream
*   **Backend Status**: Exists
*   **Required Frontend Change**: None (Documented for potential integration).

### `POST /api/v1/storage/artifacts/{artifact_id}/legal-hold`
*   **Method**: `POST`
*   **Auth Required**: Yes
*   **Request Body**:
    ```json
    {
      "hold": boolean
    }
    ```
*   **Response Shape**:
    ```json
    {
      "message": "Legal hold set to true/false successfully",
      "artifact_id": "string",
      "legal_hold": boolean
    }
    ```
*   **Backend Status**: Exists
*   **Required Frontend Change**: None.

---
*Documentation last updated: June 08, 2026*
