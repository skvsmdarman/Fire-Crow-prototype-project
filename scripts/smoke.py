from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "partial"}


@dataclass
class SmokeResult:
    name: str
    ok: bool
    detail: str


_COOKIE_OPENER = build_opener(HTTPCookieProcessor())


def safe_terminal_text(value: str) -> str:
    return value.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8"
    )


def request_json(url: str, *, method: str = "GET", token: str | None = None, body: dict[str, Any] | None = None, timeout: int = 20) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=data, headers=headers, method=method)
    with _COOKIE_OPENER.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url: str, *, timeout: int = 20) -> str:
    with _COOKIE_OPENER.open(url, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def request_status(url: str, *, method: str = "GET", timeout: int = 20) -> tuple[int, str]:
    request = Request(url, method=method)
    try:
        with _COOKIE_OPENER.open(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def wait_for_http(url: str, *, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request_text(url, timeout=3)
            return
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"{url} did not become reachable: {last_error}")


def _run_git_command(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    return completed.stdout.strip()


def _normalize_repo_url(url: str) -> str:
    value = url.strip()
    if not value:
        return ""
    if value.startswith("git@github.com:"):
        owner_repo = value.removeprefix("git@github.com:")
        return f"https://github.com/{owner_repo.removesuffix('.git')}"
    return value.removesuffix(".git")


def discover_default_repo_url() -> str:
    configured = os.getenv("FIRECROW_SMOKE_REPO_URL", "").strip()
    if configured:
        return _normalize_repo_url(configured)
    return _normalize_repo_url(_run_git_command("remote", "get-url", "origin"))


def discover_default_repo_branch() -> str:
    configured = os.getenv("FIRECROW_SMOKE_REPO_BRANCH", "").strip()
    if configured:
        return configured
    current_branch = _run_git_command("branch", "--show-current")
    return current_branch or "main"


def run_smoke(api_base: str, frontend_url: str, repo_url: str, repo_branch: str, timeout_seconds: int) -> list[SmokeResult]:
    results: list[SmokeResult] = []
    api_base = api_base.rstrip("/") + "/"
    run_id = uuid.uuid4().hex[:8]
    username = f"smoke_{run_id}"
    email = f"smoke-{run_id}@firecrow.dev"

    wait_for_http(frontend_url, timeout_seconds=timeout_seconds)
    frontend_html = request_text(frontend_url)
    signin_html = request_text(urljoin(frontend_url, "signin"))
    terms_html = request_text(urljoin(frontend_url, "terms"))
    landing_ok = ("FireCrow" in frontend_html) or ("Fire Crow" in frontend_html)
    signin_ok = ("FireCrow" in signin_html) or ("Fire Crow" in signin_html) or ("Sign in" in signin_html)
    terms_ok = ("Terms" in terms_html) or ("Privacy" in terms_html)
    results.append(
        SmokeResult(
            "frontend",
            landing_ok and signin_ok and terms_ok,
            "landing, sign-in, and terms routes served",
        )
    )

    health = request_json(urljoin(api_base, "../../health"))
    results.append(SmokeResult("backend health", health.get("status") == "up", json.dumps(health)))

    policy_context = request_json(urljoin(api_base, "auth/policy-context"))
    providers = policy_context.get("providers", {})
    oauth_hidden = not providers.get("github") and not providers.get("google")
    results.append(
        SmokeResult(
            "provider visibility",
            oauth_hidden,
            f"github={providers.get('github')} google={providers.get('google')} password={providers.get('password')}",
        )
    )

    github_status, github_body = request_status(
        urljoin(
            api_base,
            f"auth/github?privacy_policy_accepted=true&privacy_policy_version={policy_context.get('privacy_policy_version', '2026-06-06')}",
        )
    )
    google_status, google_body = request_status(
        urljoin(
            api_base,
            f"auth/google?privacy_policy_accepted=true&privacy_policy_version={policy_context.get('privacy_policy_version', '2026-06-06')}",
        )
    )
    oauth_blocked = github_status == 503 and google_status == 503
    results.append(
        SmokeResult(
            "oauth disabled path",
            oauth_blocked,
            f"github_status={github_status} google_status={google_status} github_body={github_body[:80]} google_body={google_body[:80]}",
        )
    )

    register = request_json(
        urljoin(api_base, "auth/register"),
        method="POST",
        body={
            "username": username,
            "password": "strongpassword123",
            "email": email,
            "privacy_policy_accepted": True,
            "privacy_policy_version": policy_context.get("privacy_policy_version", "2026-06-06"),
        }
    )
    register_user_id = register["user_id"]
    results.append(SmokeResult("auth register", bool(register.get("access_token")), f"user={register.get('username')} id={register_user_id}"))

    login = request_json(
        urljoin(api_base, "auth/login"),
        method="POST",
        body={
            "username": username,
            "password": "strongpassword123",
            "privacy_policy_accepted": True,
            "privacy_policy_version": policy_context.get("privacy_policy_version", "2026-06-06"),
        }
    )
    token = login["access_token"]
    results.append(SmokeResult("auth login", bool(token), f"user={login.get('username')}"))

    me = request_json(urljoin(api_base, "auth/me"), token=token)
    session = request_json(urljoin(api_base, "auth/session"), token=token)
    session_ok = me.get("user_id") == register_user_id and session.get("user_id") == register_user_id
    results.append(SmokeResult("auth me/session", session_ok, f"me={me.get('username')} session={session.get('username')} user_id={register_user_id}"))

    system_status = request_json(urljoin(api_base, "system/status"), token=token)
    results.append(
        SmokeResult(
            "system status",
            system_status.get("api") == "online" and system_status.get("database") == "connected",
            f"api={system_status.get('api')} database={system_status.get('database')} sandbox={system_status.get('sandbox_mode')}",
        )
    )

    started = time.perf_counter()
    submitted = request_json(
        urljoin(api_base, "audit/submit"),
        method="POST",
        token=token,
        body={
            "repo_url": repo_url,
            "repo_branch": repo_branch,
            "attestation_accepted": True,
            "authorization_scope": "authorized_representative",
        },
        timeout=25,
    )
    submit_ms = int((time.perf_counter() - started) * 1000)
    job_id = submitted["id"]
    results.append(SmokeResult("audit submit", submit_ms < 5000 and submitted["status"] == "queued", f"job={job_id} submit_ms={submit_ms}"))

    detail = None
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        detail = request_json(urljoin(api_base, f"audit/job/{job_id}"), token=token)
        if detail["job"]["status"] in TERMINAL_STATUSES:
            break
        time.sleep(2)

    if detail is None:
        raise RuntimeError("Job detail was never loaded")

    final_status = detail["job"]["status"]
    results.append(
        SmokeResult(
            "audit lifecycle",
            final_status in {"completed", "partial"},
            f"status={final_status} findings={len(detail.get('findings', []))} report={detail['job'].get('report_pdf_url')}",
        )
    )

    report_request = Request(urljoin(api_base, f"audit/job/{job_id}/report"), headers={"Authorization": f"Bearer {token}"})
    with _COOKIE_OPENER.open(report_request, timeout=20) as response:
        report_body = response.read(1200).decode("utf-8", errors="replace")
        report_content_type = response.headers.get("Content-Type", "")
    results.append(
        SmokeResult(
            "report retrieval",
            response.status == 200 and ("text/html" in report_content_type or "application/pdf" in report_content_type),
            f"status={response.status} content_type={report_content_type} preview={report_body[:120]}",
        )
    )

    stream_request = Request(urljoin(api_base, f"audit/{job_id}/stream"), headers={"Authorization": f"Bearer {token}"})
    with _COOKIE_OPENER.open(stream_request, timeout=20) as response:
        stream_text = response.read(16000).decode("utf-8", errors="replace")
    results.append(
        SmokeResult(
            "sse stream",
            "event: connect" in stream_text and "event: complete" in stream_text,
            "connect/log/complete events observed",
        )
    )

    for _ in range(5):
        jobs = request_json(urljoin(api_base, "audit/jobs"), token=token)
        live_session = request_json(urljoin(api_base, "auth/session"), token=token)
        if not jobs or live_session.get("user_id") != register_user_id:
            results.append(SmokeResult("repeat session/jobs", False, f"jobs={len(jobs) if isinstance(jobs, list) else 'ERR'} session={live_session}"))
            break
    else:
        results.append(SmokeResult("repeat session/jobs", True, "5 sequential session and job-list checks passed"))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a live FireCrow project smoke test against local services.")
    parser.add_argument("--api-base", default="http://localhost:8000/api/v1/")
    parser.add_argument("--frontend-url", default="http://localhost:3000/")
    parser.add_argument("--repo-url", default=discover_default_repo_url())
    parser.add_argument("--repo-branch", default=discover_default_repo_branch())
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    if not args.repo_url:
        print("[FAIL] smoke setup: no repo URL was provided and no git origin could be discovered")
        return 1

    try:
        results = run_smoke(args.api_base, args.frontend_url, args.repo_url, args.repo_branch, args.timeout)
    except Exception as exc:
        print(f"[FAIL] smoke setup: {exc}")
        return 1

    failed = False
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(safe_terminal_text(f"[{status}] {result.name}: {result.detail}"))
        failed = failed or not result.ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
