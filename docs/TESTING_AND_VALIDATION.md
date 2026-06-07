# Testing And Validation

This document is based on `package.json`, `scripts/validate.py`, `scripts/smoke.py`, `.github/workflows/ci.yml`, `pytest.ini`, and `backend/tests/*`.

## Main Commands

### Full Validation Wrapper

```powershell
npm run validate
```

Implemented by `scripts/validate.py`, which runs:

1. frontend lint
2. frontend build
3. Pyright type checking
4. backend pytest suite

## Backend Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
```

Test focus areas from `backend/tests/*`:

- auth and OAuth
- audit routes and report safety
- SSE behavior
- orchestration graph routing
- runtime finalization and cleanup
- startup and config hardening
- scan-plan logic

## Frontend Checks

```powershell
cd frontend
npm run lint
npm run build
```

These are the same checks used by `.github/workflows/ci.yml`.

## Pyright

```powershell
npx pyright --pythonpath .\.venv\Scripts\python.exe
```

This is the command shape used by `scripts/validate.py`.

## Smoke Test

```powershell
npm run smoke
```

Implemented by `scripts/smoke.py`.

The script intends to validate:

- landing page
- sign-in page
- terms page
- backend health
- auth register/login/me
- system status
- audit submission
- job lifecycle
- SSE completion

## Current Known Gaps

The smoke script currently appears out of sync with the backend:

- it calls `/system/status` without an auth token, but the route requires auth
- it submits `/audit/submit` without `attestation_accepted`, but the backend schema rejects false or missing attestation

So treat `scripts/smoke.py` as a maintenance target, not a guaranteed green check, until those mismatches are fixed.

## GitHub Actions CI

Source: `.github/workflows/ci.yml`.

The current CI runs:

- backend tests on Ubuntu with SQLite, `DEBUG=True`, and `FIRE_CROW_MOCK_SANDBOX=True`
- frontend lint and build on Ubuntu

## What Each Check Validates

| Check | Validates |
| --- | --- |
| `pytest backend/tests` | backend routes, models, startup, auth, orchestration control flow |
| `npm run lint` in `frontend/` | frontend linting |
| `npm run build` in `frontend/` | production frontend compilation |
| `npx pyright ...` | backend Python typing against the configured interpreter |
| `scripts/smoke.py` | intended full-stack local smoke flow, but currently mismatched in a few places |

## Residual Gaps

- No dedicated automated browser E2E suite is checked into this repo.
- The smoke script is currently stale relative to auth and audit-submit contracts.
- Debug-mode scanner simulations mean passing tests do not prove all external scanners are installed.
- Hosted deployment behavior for Docker-backed active stages is not fully covered by automated tests.

