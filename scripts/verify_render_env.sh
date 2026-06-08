#!/usr/bin/env bash
set -euo pipefail

# Verifies the minimum Render/backend environment needed for OAuth redirects,
# CORS, auth security, and production database safety.
# Usage after exporting env vars locally or inside a Render shell:
#   bash scripts/verify_render_env.sh

failures=0
warnings=0

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  failures=$((failures + 1))
}

warn() {
  printf 'WARN: %s\n' "$1" >&2
  warnings=$((warnings + 1))
}

pass() {
  printf 'OK: %s\n' "$1"
}

require_non_empty() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "${value}" ]]; then
    fail "${name} is required but empty."
  else
    pass "${name} is set."
  fi
}

require_url_origin() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "${value}" ]]; then
    fail "${name} is required but empty."
    return
  fi
  if [[ "${value}" == *localhost* || "${value}" == *127.0.0.1* || "${value}" == *0.0.0.0* ]]; then
    fail "${name} must not point to localhost/loopback in Render production: ${value}"
    return
  fi
  if [[ ! "${value}" =~ ^https://[^/]+/?$ ]]; then
    fail "${name} must be a deployed HTTPS origin without a path, for example https://firecrow.example.com. Current: ${value}"
    return
  fi
  pass "${name} is a deployed HTTPS origin."
}

require_non_empty DATABASE_URL
require_non_empty SECRET_KEY
require_non_empty ENCRYPTION_KEY
require_url_origin FRONTEND_URL

if [[ "${DEBUG:-}" == "true" || "${DEBUG:-}" == "True" || "${DEBUG:-}" == "1" ]]; then
  fail "DEBUG must be false in Render production."
else
  pass "DEBUG is not enabled."
fi

if [[ "${DATABASE_URL:-}" == sqlite:* ]]; then
  fail "DATABASE_URL must not use SQLite in Render production. Use Postgres."
fi

if [[ -n "${CORS_ORIGINS:-}" ]]; then
  if [[ "${CORS_ORIGINS}" == *localhost* || "${CORS_ORIGINS}" == *127.0.0.1* ]]; then
    fail "CORS_ORIGINS must not include localhost/loopback in Render production."
  elif [[ "${CORS_ORIGINS}" != *"${FRONTEND_URL:-__missing_frontend_url__}"* ]]; then
    warn "CORS_ORIGINS does not include FRONTEND_URL. Browser auth/API calls may fail."
  else
    pass "CORS_ORIGINS includes FRONTEND_URL."
  fi
else
  warn "CORS_ORIGINS is empty. Set it to FRONTEND_URL for explicit production CORS."
fi

if [[ -n "${GITHUB_CLIENT_ID:-}" || -n "${GITHUB_CLIENT_SECRET:-}" ]]; then
  require_non_empty GITHUB_CLIENT_ID
  require_non_empty GITHUB_CLIENT_SECRET
  pass "GitHub OAuth envs appear configured. Confirm provider callback URLs use the deployed backend/frontend domains."
else
  warn "GitHub OAuth envs are empty. GitHub sign-in/integration will be disabled or degraded."
fi

if [[ -n "${GOOGLE_CLIENT_ID:-}" || -n "${GOOGLE_CLIENT_SECRET:-}" ]]; then
  require_non_empty GOOGLE_CLIENT_ID
  require_non_empty GOOGLE_CLIENT_SECRET
  pass "Google OAuth envs appear configured. Confirm Google Console authorized origins/callbacks use deployed domains."
else
  warn "Google OAuth envs are empty. Google sign-in will be disabled or degraded."
fi

printf '\nRender env verification complete: %s error(s), %s warning(s).\n' "${failures}" "${warnings}"

if (( failures > 0 )); then
  exit 1
fi
