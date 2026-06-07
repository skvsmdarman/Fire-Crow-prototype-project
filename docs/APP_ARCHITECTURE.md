# Historical Note

Prefer `docs/ARCHITECTURE.md` for the current architecture overview tied to the present codebase. This file is older design/reference material.

# Fire Crow Application Architecture

This document defines the technical constraints, folder hierarchy, state sync, and building rules for the Fire Crow project.

---

## 1. Technical Stack

* **Framework & Engine**: [React 19](https://react.dev) + [Next.js 16.2](https://nextjs.org) (App Router configuration).
* **Language**: TypeScript (`^5.0.0`) configured with strict type check rules.
* **Styling System**: **Vanilla CSS**. Tailored custom CSS Variables and module files are used to maintain full flexibility. Tailwind CSS is strictly prohibited.
* **State Management**: React local state hook controls (`useState`, `useMemo`, `useCallback`) alongside `useEffect` for data-fetching.
* **Routing Engine**: Built-in Next.js App Router API (`next/navigation`).
* **Async Requests**: Fetch API with Bearer token authentication and JSON request payloads.

---

## 2. Directory Structure

```text
d:\Fire Crow\
├── backend/                  # FastAPI Application Workspace
│   ├── app/
│   │   ├── agents/           # Security audit AI agents (recon, sast, ai_analyzer)
│   │   ├── api/              # Route endpoints (auth, audit, sse, system)
│   │   ├── models/           # SQLAlchemy schemas & SQLite models
│   │   ├── orchestrator/     # Maestro queue workflow runtime
│   │   ├── schemas/          # Pydantic validation models
│   │   ├── services/         # Encryption, auth token keys, PDF & email senders
│   │   └── config.py         # Global backend environment settings
│   └── tests/                # Pytest suites
│
├── frontend/                 # Next.js Application Workspace
│   ├── public/               # Static icons, vector shapes, audit documents
│   └── src/
│       └── app/
│           ├── dashboard/    # Auditing dashboard workspace panel
│           ├── signin/       # Authentication (GitHub/Google/Local) page
│           ├── terms/        # Terms & conditions checkbox layout
│           ├── globals.css   # Main design system & custom CSS variables
│           ├── layout.tsx    # Root layout wrapping metadata & fonts
│           └── page.tsx      # Landing page / marketing page with animations
│
├── scripts/                  # CI/CD & Build validation scripts
│   └── validate.ps1          # Unified testing, building, and linting pipeline
└── package.json              # Workspace-level run tasks configuration
```

---

## 3. Session & State Persistence

Authentication tokens are cached inside client local storage to prevent session degradation on page updates.

### 3.1 Saved Session Properties
The frontend stores exactly the following keys inside `window.localStorage`:
* `fc_token`: JSON Web Token string returned by the authentication endpoints.
* `fc_username`: Cleartext name of the current authenticated user workspace.
* `fc_user_id`: Tenant identifier database code (e.g., `usr_workspace_name`).
* `fc_terms_accepted`: String value `"true"` signaling that terms and agreements are accepted.

### 3.2 State Synchronization Pattern
* **On Initial Load**: The application fetches profile validation from `/auth/me`. If a status 401 is returned, local storage keys are automatically purged, and the router pushes the user to `/signin`.
* **Tenant Isolation**: All calls to `/api/v1/audit/*` automatically pass the stored token, ensuring the backend returns only jobs owned by the user's workspace.

---

## 4. Build Validation
To prevent compile failures and syntax errors, all changes must pass validation before commits:

```bash
# Execute full validation check suite
npm run validate
```
This triggers:
1. `frontend` eslint checks (`npm run lint` in frontend).
2. Next.js production compiler build (`npm run build` in frontend).
3. Backend type safety check (`npx pyright`).
4. Pytest suite testing (`pytest backend/tests/`).
