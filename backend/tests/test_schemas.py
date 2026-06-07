from datetime import datetime
import pytest

from pydantic import ValidationError

from backend.app.schemas.audit_api import SubmitJobRequest
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


def test_submit_job_request_normalizes_empty_branch():
    request = SubmitJobRequest(repo_url="https://github.com/example/repo", repo_branch="  ")

    assert request.repo_branch == "main"


@pytest.mark.parametrize("branch", ["../main", "/main", "feature//x", "feature.lock", "release@{1}", ".hidden"])
def test_submit_job_request_rejects_unsafe_branch_refs(branch: str):
    with pytest.raises(ValidationError):
        SubmitJobRequest(repo_url="https://github.com/example/repo", repo_branch=branch)


def test_audit_state_dict_reducer():
    from backend.app.schemas.audit_state import merge_dicts
    
    d1 = {"recon": {"status": "executed"}}
    d2 = {"regex_sast": {"status": "executed"}}
    merged = merge_dicts(d1, d2)
    assert merged == {
        "recon": {"status": "executed"},
        "regex_sast": {"status": "executed"}
    }
    
    assert merge_dicts(None, {"x": 1}) == {"x": 1}
    assert merge_dicts({"y": 2}, None) == {"y": 2}
