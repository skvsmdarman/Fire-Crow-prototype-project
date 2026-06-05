from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "partial"}


@dataclass
class SmokeResult:
    name: str
    ok: bool
    detail: str


def request_json(url: str, *, method: str = "GET", token: str | None = None, body: dict[str, Any] | None = None, timeout: int = 20) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url: str, *, timeout: int = 20) -> str:
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


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


def run_smoke(api_base: str, frontend_url: str, repo_url: str, repo_branch: str, timeout_seconds: int) -> list[SmokeResult]:
    results: list[SmokeResult] = []
    api_base = api_base.rstrip("/") + "/"

    wait_for_http(frontend_url, timeout_seconds=timeout_seconds)
    frontend_html = request_text(frontend_url)
    signin_html = request_text(urljoin(frontend_url, "signin"))
    terms_html = request_text(urljoin(frontend_url, "terms"))
    results.append(
        SmokeResult(
            "frontend",
            "FireCrow" in frontend_html and "FireCrow" in signin_html and "Terms" in terms_html,
            "landing, sign-in, and terms routes served",
        )
    )

    health = request_json(urljoin(api_base, "../../health"))
    results.append(SmokeResult("backend health", health.get("status") == "up", json.dumps(health)))

    login = request_json(urljoin(api_base, "auth/login"), method="POST", body={"username": "smoke"})
    token = login["access_token"]
    results.append(SmokeResult("auth login", bool(token), f"user={login.get('username')}"))

    me = request_json(urljoin(api_base, "auth/me"), token=token)
    results.append(SmokeResult("auth me", me.get("user_id") == "usr_smoke", json.dumps(me)))

    system_status = request_json(urljoin(api_base, "system/status"))
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
        body={"repo_url": repo_url, "repo_branch": repo_branch},
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

    stream_request = Request(urljoin(api_base, f"audit/{job_id}/stream"), headers={"Authorization": f"Bearer {token}"})
    with urlopen(stream_request, timeout=20) as response:
        stream_text = response.read(16000).decode("utf-8", errors="replace")
    results.append(
        SmokeResult(
            "sse stream",
            "event: connect" in stream_text and "event: complete" in stream_text,
            "connect/log/complete events observed",
        )
    )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a live FireCrow project smoke test against local services.")
    parser.add_argument("--api-base", default="http://localhost:8000/api/v1/")
    parser.add_argument("--frontend-url", default="http://localhost:3000/")
    parser.add_argument("--repo-url", default="https://github.com/octocat/Hello-World")
    parser.add_argument("--repo-branch", default="master")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    try:
        results = run_smoke(args.api_base, args.frontend_url, args.repo_url, args.repo_branch, args.timeout)
    except Exception as exc:
        print(f"[FAIL] smoke setup: {exc}")
        return 1

    failed = False
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
        failed = failed or not result.ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
