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

Primary backend calls:

- `GET /audit/jobs`
- `GET /audit/job/{id}`
- `DELETE /audit/job/{id}`
- `POST /audit/submit`
- `GET /system/status`
- `GET /audit/{id}/stream`
- `GET /audit/job/{id}/report`

Important dashboard subcomponents:

- `frontend/src/features/audits/components/AuditForm.tsx`
- `JobList.tsx`
- `PipelineViz.tsx`
- `LogStream.tsx`
- `Sidebar.tsx`
- `frontend/src/features/findings/components/FindingsList.tsx`

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

## Auth Session Storage

Source: `frontend/src/lib/authSession.ts`, `frontend/src/shared/hooks/useAuthSession.ts`.

Stored keys:

- `fc_token`
- `fc_user_id`
- `fc_username`
- `fc_workspace`

Behavior:

- auth state is broadcast through a custom browser event
- logout attempts server-side logout, then clears local storage even if the request fails

## Policy And Legal Pages

Sources:

- `frontend/src/app/privacy-policy/page.tsx`
- `frontend/src/app/terms/page.tsx`
- `frontend/src/lib/policyData.ts`
- `frontend/src/lib/policy.ts`

Current behavior:

- pages log policy link clicks and page views through `POST /auth/policy-events`
- region-specific text is selected using client timezone

Current caution:

- `policyData.ts` includes claims about Neon, R2, GDPR/DPDP/CCPA compliance, SLAs, and subscription terms that are not fully backed by the backend codebase

## PWA And Offline Behavior

Sources:

- `frontend/src/app/layout.tsx`
- `frontend/src/components/PWARegister.tsx`
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

## Known Frontend Cleanup Needs

- Audit submission does not send the backend-required attestation fields.
- `SubmitAuditBody` still declares `scanners` and `sandbox_mode`, but the current backend submit route does not accept those options.
- The dashboard expects fields like `sandbox_mode` and `integrations` even though `/system/status` only returns them for admin-like users.
- Legal and signup copy overstates current backend guarantees.

