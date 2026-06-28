# Configuration

This document is derived from `backend/app/config.py`, `backend/.env.example`, `frontend/.env.example`, `frontend/src/shared/api/client.ts`, `backend/app/services/storage.py`, and `backend/app/services/reporter.py`.

## Load Order

Backend settings load in this order from `backend/app/config.py`:

1. `.env`
2. `backend/.env`
3. `.env.local`
4. `backend/.env.local`

Later files win.

## Backend Environment Variables

### Server And Request Handling

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `PORT` | optional | `8000` | backend port | example present |
| `HOST` | optional | `0.0.0.0` | backend bind host | example present |
| `DEBUG` | optional | `false` | toggles debug behavior | local example sets `true` |
| `SECRET_KEY` | required in non-debug | empty string | JWT signing and security hashing input | sensitive; production must be strong and >= 32 chars |
| `ENCRYPTION_KEY` | required in non-debug | empty string | provider-token encryption key | sensitive; production must be strong and >= 32 chars |
| `FRONTEND_URL` | optional | `http://localhost:3000` | frontend origin and redirect base | can be filled from `RENDER_EXTERNAL_URL` |
| `CORS_ORIGINS` | optional | empty string | extra allowed CORS origins | used in code; example missing |
| `MAX_REQUEST_BODY_BYTES` | optional | `10485760` | request body limit | used in middleware; example missing |
| `MAX_JSON_BODY_BYTES` | optional | `2097152` | JSON body limit constant | defined in config; not obviously enforced separately |

### Policy And Auth

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `PRIVACY_POLICY_VERSION` | optional | `2026-06-06` | backend policy version | code uses it directly; example missing |
| `TERMS_VERSION` | optional | `2026-06-06` | backend terms version | code uses it directly; example missing |
| `GITHUB_OAUTH_SCOPES` | optional | `["repo","workflow","read:org","user:email"]` | GitHub OAuth scope list | example missing |
| `LOGIN_FAILURE_WINDOW_MINUTES` | optional | `10` | login lockout window | example missing |
| `LOGIN_FAILURE_LIMIT` | optional | `5` | max failed logins per window | example missing |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | optional | `1440` | access-token lifetime | example missing |
| `AUTH_COOKIE_NAME` | optional | `fc_access_token` | cookie key | example missing |
| `AUTH_COOKIE_SECURE` | optional | `true` | secure cookie flag | example missing |
| `AUTH_COOKIE_HTTPONLY` | optional | `true` | httpOnly cookie flag | example missing |
| `AUTH_COOKIE_SAMESITE` | optional | `lax` | SameSite value | example missing |

### Database And Queue

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | required for useful runtime | `postgresql://postgres:postgres@localhost:5432/firecrow` | primary DB connection string | production rejects SQLite; example recommends SQLite for local debug |
| `REDIS_URL` | optional | empty string | Celery broker/result backend and token/login cache | example present |
| `REDIS_PASSWORD` | optional | empty string | password injected into `REDIS_URL` if needed | example present |
| `BROKER_CONNECTION_TIMEOUT` | optional | `0.5` | broker timeout setting | defined in config; example missing |

### Sandbox And Scanner Runtime

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `FIRE_CROW_MOCK_SANDBOX` | optional | `false` | force sandbox simulation | example present |
| `FIRE_CROW_ALLOW_UNTRUSTED_DOCKERFILE_BUILD` | optional | `false` | allow building target Dockerfiles | sensitive; example present |
| `FIRE_CROW_SCANNER_IMAGE` | optional | `ghcr.io/johan-droid/firecrow-scanner:2026-06-06` | scanner/Kali image | production rejects `:latest`; example present |
| `SANDBOX_PYTHON_IMAGE` | optional | `python:3.12-alpine` | fallback target image for Python repos | example missing |
| `SANDBOX_NODE_IMAGE` | optional | `node:20-alpine` | fallback target image for Node repos | example missing |
| `SCANNER_COMMAND_TIMEOUT` | optional | `600` | scanner command timeout budget | example missing |
| `SCANNER_OUTPUT_MAX_LENGTH` | optional | `50000` | scanner output truncation budget | example missing |
| `API_DISCOVERY_LIMIT` | optional | `50` | max API paths copied into runtime state | example missing |

### GitHub And Google OAuth

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `GITHUB_CLIENT_ID` | optional | empty string | GitHub OAuth client ID | example present |
| `GITHUB_CLIENT_SECRET` | optional | empty string | GitHub OAuth client secret | sensitive; example present |
| `GITHUB_TOKEN` | optional | empty string | GitHub REST/GitMCP fallback writes | sensitive; example present |
| `GOOGLE_CLIENT_ID` | optional | empty string | Google OAuth client ID | used in code; example missing |
| `GOOGLE_CLIENT_SECRET` | optional | empty string | Google OAuth client secret | sensitive; used in code; example missing |

### Email Delivery

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `RESEND_API_KEY` | optional | empty string | Resend mail delivery | sensitive; example present |
| `BREVO_API_KEY` | optional | empty string | Brevo mail delivery | sensitive; example present |
| `SENDER_EMAIL` | optional | empty string | sender address for mailers | set this when using Resend or Brevo |
| `SMTP_HOST` | optional | `smtp.gmail.com` | SMTP server | example present |
| `SMTP_PORT` | optional | `587` | SMTP port | example present |
| `SMTP_USER` | optional | empty string | SMTP username | sensitive; example present |
| `SMTP_PASSWORD` | optional | empty string | SMTP password | sensitive; example present |

### Artifact Storage

No external object storage is used. All artifacts (reports, evidence, attack graphs) are stored in Neon PostgreSQL as TEXT/JSONB, and temporary PDFs are generated only when needed for download or email delivery.

### AI Settings

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `GEMINI_API_KEY` | optional | empty string | Gemini access for AI stages | sensitive; example present |
| `OPENAI_API_KEY` | optional | empty string | optional OpenAI key | example present |
| `GEMINI_MODEL` | optional | empty string | primary Gemini model | example missing |
| `GEMINI_FALLBACK_MODEL` | optional | empty string | fallback Gemini model | example missing |
| `GEMINI_ENABLE_FALLBACK_MODEL` | optional | `true` | enable Gemini fallback | example missing |
| `GEMINI_MAX_ATTEMPTS` | optional | `3` | attempt budget constant | defined in config; example missing |
| `GEMINI_TIMEOUT_SECONDS` | optional | `30` | Gemini call timeout | example missing |
| `GEMINI_MAX_FINDINGS_PER_CALL` | optional | `50` | AI batch size cap | example missing |
| `GEMINI_MAX_PROMPT_CHARS` | optional | `100000` | prompt truncation cap | example missing |
| `GEMINI_DAILY_SOFT_LIMIT` | optional | `1000` | quota guard constant | example missing |
| `GEMINI_MIN_SECONDS_BETWEEN_CALLS` | optional | `1` | throttle constant | example missing |
| `GEMINI_FINDINGS_CHUNK_SIZE` | optional | `50` | chunk size constant | example missing |
| `LLM_CHAT_ASSISTANT` | optional | `false` | Enables interactive chat assistant | defaults to `false` |
| `LLM_DASHBOARD_INSIGHT` | optional | `false` | Generates dashboard summary insights | defaults to `false` |
| `LLM_ATTACK_CHAIN_NAMING` | optional | `false` | Generates names for attack chains | defaults to `false` |
| `LLM_PR_DESCRIPTION` | optional | `false` | Generates pull request descriptions | defaults to `false` |

### Job, Budget, And Scoring Tunables

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `MAX_ACTIVE_JOBS_PER_USER` | optional | `5` | per-user queued/running cap | example missing |
| `SSE_POLL_INTERVAL` | optional | `0.5` | intended SSE polling setting | current SSE route uses fixed values instead |
| `SSE_HEARTBEAT_INTERVAL` | optional | `15.0` | intended SSE heartbeat setting | current SSE route uses fixed values instead |
| `MAX_SCAN_DURATION` | optional | `2700` | scan budget in seconds | example missing |
| `DEFAULT_BUDGET_USD` | optional | `5.0` | cost budget placeholder | example missing |
| `SCORING_CRITICAL` | optional | `9.8` | critical threshold constant | example missing |
| `SCORING_HIGH` | optional | `8.5` | high threshold constant | example missing |
| `SCORING_MEDIUM` | optional | `5.5` | medium threshold constant | example missing |
| `SCORING_LOW` | optional | `2.5` | low threshold constant | example missing |
| `SCORING_INFO` | optional | `0.0` | info threshold constant | example missing |

### Report Rendering

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `REPORT_COMPACT_MODE` | optional | `false` | report layout flag | example missing |
| `REPORT_MAX_PAGES` | optional | `50` | report size cap | example missing |
| `REPORT_MAX_FINDINGS_IN_PDF` | optional | `100` | findings-per-report cap | example missing |
| `REPORT_MAX_EVIDENCE_CHARS` | optional | `2000` | evidence truncation cap | example missing |
| `REPORT_MAX_REMEDIATION_CHARS` | optional | `2000` | remediation truncation cap | example missing |
| `REPORT_INCLUDE_DETAILED_FINDINGS` | optional | `true` | detailed findings flag | example missing |
| `REPORT_STORE_FULL_ARTIFACT_JSON` | optional | `true` | artifact JSON retention flag | example missing |

## Legacy Alias Variables Used In Code

These are not part of `Settings`, but they are still checked directly in code and are missing from the examples:

| Variable | Used by | Purpose |
| --- | --- | --- |
| `RENDER_EXTERNAL_URL` | `backend/app/config.py` | fallback source for `FRONTEND_URL` |

## Frontend Environment Variables

| Variable | Required | Default | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | recommended | none at build time | frontend API base URL | example present; launcher injects it during `npm run dev` |

If unset in the browser:

- `frontend/src/shared/api/client.ts` falls back to `http://localhost:8000/api/v1` only for `localhost:3000` and `127.0.0.1:3000`
- otherwise it falls back to `/api/v1`

## Practical Notes

- Copying the example files matters. Bare config defaults are not the recommended local setup.
- Production mode is intentionally stricter than debug mode.
- Several config constants exist in code without matching entries in `.env.example`; those are now documented here but still worth adding to examples in a later change.

---
*Documentation last updated: June 08, 2026*
