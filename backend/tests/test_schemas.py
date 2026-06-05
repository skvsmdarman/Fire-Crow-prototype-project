from datetime import datetime
from backend.app.schemas import AuditState, JobStatus, Finding, Severity


def test_audit_state_initialization():
    state = AuditState(
        job_id="test-job-id-123",
        user_id="test-user-id-456",
        repo_url="https://github.com/example/repo"
    )

    assert state.job_id == "test-job-id-123"
    assert state.user_id == "test-user-id-456"
    assert state.repo_url == "https://github.com/example/repo"
    assert state.status == JobStatus.QUEUED
    assert isinstance(state.created_at, datetime)
    assert len(state.static_findings) == 0
    assert len(state.errors) == 0


def test_finding_validation():
    finding = Finding(
        id="finding-1",
        agent_source="SAST",
        title="SQL Injection Vulnerability",
        description="Found SQL Injection in route /users",
        severity=Severity.HIGH,
        cvss_score=8.5
    )

    assert finding.id == "finding-1"
    assert finding.severity == Severity.HIGH
    assert finding.cvss_score == 8.5
