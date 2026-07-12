from __future__ import annotations

from urllib.parse import quote

from app.config import settings


def get_frontend_base_url() -> str:
    configured = settings.FRONTEND_URL.strip()
    if configured:
        return configured.rstrip("/")
    return "http://localhost:3000"


def build_frontend_url(path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{get_frontend_base_url()}{normalized}"


def build_audit_job_url(job_id: str) -> str:
    return build_frontend_url(f"/dashboard/audits/default?jobId={quote(job_id, safe='')}")
