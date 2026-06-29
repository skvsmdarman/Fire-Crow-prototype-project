# Frontend Structure

This document describes the current Next.js app under `frontend/src/`.

## App Router Pages

Primary pages:

- `frontend/src/app/page.tsx`: public landing page
- `frontend/src/app/signin/page.tsx`: sign-in flow
- `frontend/src/app/signup/page.tsx`: sign-up flow
- `frontend/src/app/dashboard/page.tsx`: authenticated dashboard
- `frontend/src/app/privacy-policy/page.tsx`: privacy page
- `frontend/src/app/terms/page.tsx`: terms page
- `frontend/src/app/offline/page.tsx`: offline fallback

## Landing Page

Source: `frontend/src/app/page.tsx`.

Current behavior:

- marketing-style overview of platform concepts
- reads auth session from `frontend/src/lib/authSession.ts`
- routes signed-in users toward `/dashboard`
- does not call the backend directly

Current note:

- landing-page workflow copy is intentionally less fake than older versions, but some listed "agents" are still broader than what the system-status route returns.

## Sign-In Flow

Source: `frontend/src/app/signin/page.tsx`.

Backend calls:

- `GET /auth/policy-context`
- `POST /auth/login`
- `POST /auth/exchange`
- `GET /auth/{provider}`

Session behavior:

- stores token, user ID, username, and workspace in local storage
- redirects to `/dashboard?workspace=...`

## Sign-Up Flow

Source: `frontend/src/app/signup/page.tsx`.

Backend calls:

- `GET /auth/policy-context`
- `POST /auth/register`
- `GET /auth/{provider}`

Current caution:

- the page still contains marketing copy such as "6 offensive agents", "Neon", and guaranteed mailbox delivery that is not grounded in current backend implementation.

## Dashboard

Source: `frontend/src/app/dashboard/page.tsx`.

The dashboard is structured modularly to separate business state machine logic from presentation layouts:

- **Orchestrator Page (`page.tsx`)**: Coordinates visual transitions, page navigation (Overview, Audits, Findings, Reports, Settings), dynamic chat assistant widgets, and offline/reconnecting banner states.
- **Subcomponents (`components.tsx`)**: Declares display-only structures such as `OverviewSection`, `AuditLaunchPanel`, `AuditJobList`, `AuditJobDetail`, `FindingsPanel`, `ReportsPanel`, `SettingsPanel`, and `DashboardSidebar`.
- **State Hooks (`hooks.ts`)**: Encapsulates functional state hooks:
  - `useDashboardStatus`: System status polling adapter and derived overview indicators.
  - `useSessionValidation`: Checks token status resiliently, transitioning to an `isReconnecting` offline state during temporary disconnections instead of immediate session clearing.
  - `useAuditSubmission`: Controls repository url/branch parameters and enforces the mandatory explicit security authorization attestation.
  - `useReportDownload`: Handles backend blob downloads with unique request tracing ID error logging.

Primary backend calls:

- `GET /audit/jobs`
- `GET /audit/job/{id}`
- `DELETE /audit/job/{id}`
- `POST /audit/submit` (with attestation verification fields)
- `GET /system/status`
- `GET /audit/{id}/stream`
- `GET /audit/job/{id}/report`

## Shared Components

Key folders:

- `frontend/src/components/*`
- `frontend/src/components/ui/*`
- `frontend/src/shared/components/*`

Notable shared pieces:

- `Toast`
- `Button`
- `Card`
- `Input`
- `Badge`
- `FireCrowLoader`
- `PWARegister`

## API Base URL Logic

Source: `frontend/src/shared/api/client.ts`.

- uses `NEXT_PUBLIC_API_URL` when present
- otherwise falls back to localhost `8000` only for `localhost:3000` and `127.0.0.1:3000`
- otherwise falls back to `/api/v1`

Practical implication:

- the root launcher matters for dynamic port assignment because it injects the backend URL into the frontend process

## Auth Session Storage & Lifecycle

Source: `frontend/src/lib/authSession.ts`, `frontend/src/shared/hooks/useAuthSession.ts`.

Stored keys:

- `fc_token`
- `fc_user_id`
- `fc_username`
- `fc_workspace`

Behavior:

- Auth state is broadcast through a custom browser event.
- Network validation of sessions has three outcomes: `"valid"`, `"invalid"`, and `"network_error"`. If the server returns a temporary network error, the local session is retained, and the dashboard transitions into a read-only reconnecting banner state rather than forcing an immediate logout.

## Policy And Legal Pages

Sources:

- `frontend/src/app/privacy-policy/page.tsx`
- `frontend/src/app/terms/page.tsx`
- `frontend/src/lib/policyData.ts`
- `frontend/src/lib/policy.ts`

Current behavior:

- pages log policy link clicks and page views through `POST /auth/policy-events`
- region-specific text is selected using client timezone

## PWA And Offline Behavior

Sources:

- `frontend/src/app/layout.tsx`
- `components/PWARegister.tsx`
- `frontend/public/manifest.webmanifest`
- `frontend/public/sw.js`
- `frontend/src/app/offline/page.tsx`

Current behavior:

- service worker is registered only in production builds
- caches only the app shell and static assets
- bypasses API, auth, dashboard, report, and findings routes
- offline page explicitly states that private audit data is not cached offline

## Frontend To Backend Mapping

| Frontend file | Endpoint(s) |
| --- | --- |
| `src/app/signin/page.tsx` | `/auth/login`, `/auth/exchange`, `/auth/{provider}` |
| `src/app/signup/page.tsx` | `/auth/register`, `/auth/{provider}`, `/auth/policy-context` |
| `src/app/dashboard/page.tsx` | `/audit/*`, `/system/status`, `/auth/logout`, `/audit/{job_id}/stream` |
| `src/lib/policy.ts` | `/auth/policy-events` |
| `src/features/auth/hooks.ts` | `/auth/policy-context` |

## Grounded Product Philosophy Cleanup

- Removed ungrounded marketing claims (such as "14 agents active", "0-days", specific accuracy or timing percentages) from landing, workflow, and modules pages.
- Standardized copy on a grounded SaaS model: authorization-only scanning and evidence-backed findings.
- Hardened audit submission to prevent accidental or unverified job execution.

---
*Documentation last updated: June 29, 2026*
