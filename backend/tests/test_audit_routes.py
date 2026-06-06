from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.api.routes_auth import PRIVACY_POLICY_VERSION
from backend.app.models import AgentLog, AuditJob, FindingModel, SessionLocal
from backend.app.schemas import JobStatus, Severity

client = TestClient(app)


def _auth_headers(username: str = "auditor") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "supersecretpassword",
            "privacy_policy_accepted": True,
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "supersecretpassword",
            "privacy_policy_accepted": True,
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_jobs_returns_only_current_user_jobs():
    db = SessionLocal()
    try:
        db.add_all(
            [
                AuditJob(id="job-1", user_id="usr_auditor", repo_url="https://example.com/one", repo_branch="main"),
                AuditJob(id="job-2", user_id="usr_auditor", repo_url="https://example.com/two", repo_branch="develop"),
                AuditJob(id="job-3", user_id="usr_other", repo_url="https://example.com/other", repo_branch="main"),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/audit/jobs", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert {job["id"] for job in payload} == {"job-1", "job-2"}
    assert all(job["user_id"] == "usr_auditor" for job in payload)
    assert all(isinstance(job["created_at"], str) and "T" in job["created_at"] for job in payload)


def test_get_job_detail_serializes_findings():
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-detail",
                user_id="usr_auditor",
                repo_url="https://example.com/repo",
                repo_branch="main",
                status=JobStatus.RUNNING,
            )
        )
        db.add(
            FindingModel(
                id="finding-1",
                job_id="job-detail",
                agent_source="SAST",
                title="SQL Injection",
                description="Unsanitized query builder",
                severity=Severity.CRITICAL,
                cvss_score=9.8,
                cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                evidence="SELECT * FROM users",
                remediation="Use parameterized queries",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/audit/job/job-detail", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["id"] == "job-detail"
    assert payload["findings"][0]["severity"] == "critical"
    assert payload["findings"][0]["title"] == "SQL Injection"


def test_submit_audit_dispatches_celery_task(monkeypatch):
    calls = []

    def fake_apply_async(*, kwargs, task_id):
        calls.append({"kwargs": kwargs, "task_id": task_id})

    monkeypatch.setattr("backend.app.api.routes_audit._is_broker_reachable", lambda: True)
    monkeypatch.setattr("backend.app.api.routes_audit.run_audit_job_task.apply_async", fake_apply_async)

    response = client.post(
        "/api/v1/audit/submit",
        json={"repo_url": "https://github.com/example/repo", "repo_branch": "main"},
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["repo_url"] == "https://github.com/example/repo"
    assert payload["status"] == "queued"
    assert payload["cancel_requested"] is False
    assert payload["cancel_requested_at"] is None
    assert len(calls) == 1
    assert calls[0]["task_id"] == payload["id"]
    assert calls[0]["kwargs"]["user_id"] == "usr_auditor"


def test_submit_audit_enforces_active_job_limit(monkeypatch):
    calls = []

    def fake_apply_async(*, kwargs, task_id):
        calls.append({"kwargs": kwargs, "task_id": task_id})

    db = SessionLocal()
    try:
        for index in range(5):
            db.add(
                AuditJob(
                    id=f"job-active-{index}",
                    user_id="usr_auditor",
                    repo_url=f"https://example.com/repo-{index}",
                    repo_branch="main",
                    status=JobStatus.RUNNING,
                )
            )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("backend.app.api.routes_audit._is_broker_reachable", lambda: True)
    monkeypatch.setattr("backend.app.api.routes_audit.run_audit_job_task.apply_async", fake_apply_async)

    response = client.post(
        "/api/v1/audit/submit",
        json={"repo_url": "https://github.com/example/repo", "repo_branch": "main"},
        headers=_auth_headers(),
    )

    assert response.status_code == 429
    assert calls == []


def test_cancel_job_sets_cancel_intent_without_forcing_terminal_state():
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-cancel-route",
                user_id="usr_auditor",
                repo_url="https://example.com/cancel",
                repo_branch="main",
                status=JobStatus.RUNNING,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.delete("/api/v1/audit/job/job-cancel-route", headers=_auth_headers())

    assert response.status_code == 200
    db = SessionLocal()
    try:
        job = db.query(AuditJob).filter(AuditJob.id == "job-cancel-route").first()
        assert job is not None
        assert job.status == JobStatus.RUNNING
        assert job.cancel_requested is True
        assert job.cancel_requested_at is not None
    finally:
        db.close()


def test_download_report_serves_local_report(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.app.api.routes_audit.REPORTS_DIR", tmp_path)
    (tmp_path / "job-report.pdf").write_bytes(b"%PDF-1.4 test report")

    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-report",
                user_id="usr_auditor",
                repo_url="https://example.com/report",
                repo_branch="main",
                status=JobStatus.COMPLETED,
                report_pdf_url="/reports/job-report.pdf",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/audit/job/job-report/report", headers=_auth_headers())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-1.4")


@pytest.mark.parametrize("report_url", ["/reports/../secret.pdf", "file:///tmp/report.pdf", "https://evil.example/report.pdf"])
def test_download_report_rejects_unsafe_report_locations(report_url: str):
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-unsafe-report",
                user_id="usr_auditor",
                repo_url="https://example.com/report",
                repo_branch="main",
                status=JobStatus.COMPLETED,
                report_pdf_url=report_url,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/audit/job/job-unsafe-report/report", headers=_auth_headers())

    assert response.status_code == 400


def test_system_status_requires_auth_and_scopes_stats_to_current_user():
    db = SessionLocal()
    try:
        db.add_all(
            [
                AuditJob(id="job-system-user", user_id="usr_auditor", repo_url="https://example.com/user", repo_branch="main"),
                AuditJob(id="job-system-other", user_id="usr_other", repo_url="https://example.com/other", repo_branch="main"),
            ]
        )
        db.add_all(
            [
                FindingModel(
                    job_id="job-system-user",
                    agent_source="SAST",
                    title="User finding",
                    description="Current tenant finding",
                    severity=Severity.HIGH,
                ),
                FindingModel(
                    job_id="job-system-other",
                    agent_source="SAST",
                    title="Other finding",
                    description="Another tenant finding",
                    severity=Severity.CRITICAL,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    unauthenticated = client.get("/api/v1/system/status")
    response = client.get("/api/v1/system/status", headers=_auth_headers())

    assert unauthenticated.status_code == 401
    assert response.status_code == 200
    assert response.json()["stats"] == {"jobs": 1, "findings": 1}


@pytest.mark.parametrize("status_value", ["completed", "failed", "cancelled", "partial"])
def test_sse_stream_emits_terminal_event_for_terminal_statuses(status_value: str):
    status = JobStatus(status_value)
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id=f"job-sse-{status_value}",
                user_id="usr_auditor",
                repo_url="https://example.com/repo",
                repo_branch="main",
                status=status,
                report_pdf_url="file:///tmp/report.pdf" if status in {JobStatus.COMPLETED, JobStatus.PARTIAL} else None,
                error_message="boom" if status in {JobStatus.FAILED, JobStatus.PARTIAL} else None,
            )
        )
        db.add(
            AgentLog(
                job_id=f"job-sse-{status_value}",
                agent_name="MAESTRO",
                log_level="INFO",
                message="terminal log",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/v1/audit/job-sse-{status_value}/stream", headers=_auth_headers())

    assert response.status_code == 200
    assert "event: complete" in response.text
    assert f"\"status\": \"{status_value}\"" in response.text
