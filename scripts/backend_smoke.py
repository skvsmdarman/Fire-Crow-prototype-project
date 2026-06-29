from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "partial"}
CSRF_COOKIE_NAME = "fc_csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


@dataclass
class SmokeResult:
    name: str
    ok: bool
    detail: str


_COOKIE_JAR = CookieJar()
_COOKIE_OPENER = build_opener(HTTPCookieProcessor(_COOKIE_JAR))


def safe_terminal_text(value: str) -> str:
    return value.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8"
    )


def get_cookie_value(name: str) -> str | None:
    for cookie in _COOKIE_JAR:
        if cookie.name == name:
            return cookie.value
    return None


def request_json(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 20,
) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        csrf_token = get_cookie_value(CSRF_COOKIE_NAME)
        if csrf_token:
            headers[CSRF_HEADER_NAME] = csrf_token
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=data, headers=headers, method=method)
    with _COOKIE_OPENER.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_http(url: str, *, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with _COOKIE_OPENER.open(url, timeout=3) as response:
                response.read(16)
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
    return _normalize_repo_url(_run_git_command("remote", "get-url", "origin"))


def discover_default_repo_branch() -> str:
    return _run_git_command("branch", "--show-current") or "main"


def run_backend_smoke(
    api_base: str,
    repo_url: str,
    repo_branch: str,
    timeout_seconds: int,
    require_findings: int,
) -> list[SmokeResult]:
    results: list[SmokeResult] = []
    api_base = api_base.rstrip("/") + "/"
    run_id = uuid.uuid4().hex[:8]
    username = f"smoke_{run_id}"
    email = f"smoke-{run_id}@firecrow.dev"

    health_url = urljoin(api_base, "../../health")
    wait_for_http(health_url, timeout_seconds=timeout_seconds)
    health = request_json(health_url)
    results.append(SmokeResult("backend health", health.get("status") == "up", json.dumps(health)))

    policy_context = request_json(f"{api_base}auth/policy-context")
    privacy_version = policy_context.get("privacy_policy_version", "2026-06-06")
    results.append(
        SmokeResult(
            "policy context",
            isinstance(policy_context.get("providers"), dict),
            f"privacy_version={privacy_version} providers={policy_context.get('providers')}",
        )
    )

    register = request_json(
        f"{api_base}auth/register",
        method="POST",
        body={
            "username": username,
            "password": "strongpassword123",
            "email": email,
            "privacy_policy_accepted": True,
            "privacy_policy_version": privacy_version,
        },
    )
    user_id = register["user_id"]
    results.append(SmokeResult("auth register", bool(register.get("access_token")), f"user={username} id={user_id}"))

    login = request_json(
        f"{api_base}auth/login",
        method="POST",
        body={
            "username": username,
            "password": "strongpassword123",
            "privacy_policy_accepted": True,
            "privacy_policy_version": privacy_version,
        },
    )
    token = login["access_token"]
    results.append(SmokeResult("auth login", bool(token), f"user={login.get('username')}"))

    me = request_json(f"{api_base}auth/me", token=token)
    session = request_json(f"{api_base}auth/session", token=token)
    results.append(
        SmokeResult(
            "auth me/session",
            me.get("user_id") == user_id and session.get("user_id") == user_id,
            f"me={me.get('username')} session={session.get('username')} user_id={user_id}",
        )
    )

    system_status = request_json(f"{api_base}system/status", token=token)
    results.append(
        SmokeResult(
            "system status",
            system_status.get("api") == "online" and system_status.get("database") == "connected",
            f"api={system_status.get('api')} database={system_status.get('database')} sandbox={system_status.get('sandbox_mode')}",
        )
    )

    started = time.perf_counter()
    submitted = request_json(
        f"{api_base}audit/submit",
        method="POST",
        token=token,
        body={
            "repo_url": repo_url,
            "repo_branch": repo_branch,
            "attestation_accepted": True,
            "authorization_scope": "full_active",
        },
        timeout=25,
    )
    submit_ms = int((time.perf_counter() - started) * 1000)
    job_id = submitted["id"]
    results.append(SmokeResult("audit submit", submit_ms < 5000, f"job={job_id} submit_ms={submit_ms}"))

    detail = None
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        detail = request_json(f"{api_base}audit/job/{job_id}", token=token)
        if detail["job"]["status"] in TERMINAL_STATUSES:
            break
        time.sleep(2)

    if detail is None:
        raise RuntimeError("Job detail was never loaded")

    findings_count = len(detail.get("findings", []))
    final_status = detail["job"]["status"]
    results.append(
        SmokeResult(
            "audit lifecycle",
            final_status in {"completed", "partial"} and findings_count >= require_findings,
            f"status={final_status} findings={findings_count}",
        )
    )

    report_request = Request(
        f"{api_base}audit/job/{job_id}/report",
        headers={"Authorization": f"Bearer {token}"},
    )
    with _COOKIE_OPENER.open(report_request, timeout=20) as response:
        report_preview = response.read(1200).decode("utf-8", errors="replace")
        content_type = response.headers.get("Content-Type", "")
        status_code = response.status
    results.append(
        SmokeResult(
            "report retrieval",
            status_code == 200 and ("text/html" in content_type or "application/pdf" in content_type),
            f"status={status_code} content_type={content_type} preview={report_preview[:120]}",
        )
    )

    stream_request = Request(
        f"{api_base}audit/{job_id}/stream",
        headers={"Authorization": f"Bearer {token}"},
    )
    with _COOKIE_OPENER.open(stream_request, timeout=20) as response:
        stream_text = response.read().decode("utf-8", errors="replace")
    results.append(
        SmokeResult(
            "sse stream",
            "event: connect" in stream_text and "event: complete" in stream_text,
            "connect/log/complete events observed",
        )
    )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an API-only Fire Crow smoke test against a live backend.")
    parser.add_argument("--api-base", default="http://localhost:8000/api/v1/")
    parser.add_argument("--repo-url", default=discover_default_repo_url())
    parser.add_argument("--repo-branch", default=discover_default_repo_branch())
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--require-findings", type=int, default=1)
    args = parser.parse_args()

    if not args.repo_url:
        print("[FAIL] smoke setup: no repo URL was provided and no git origin could be discovered")
        return 1

    try:
        results = run_backend_smoke(
            api_base=args.api_base,
            repo_url=args.repo_url,
            repo_branch=args.repo_branch,
            timeout_seconds=args.timeout,
            require_findings=args.require_findings,
        )
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
