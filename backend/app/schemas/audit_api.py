from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, field_validator, Field
import re
from backend.app.schemas.audit_state import JobStatus

if TYPE_CHECKING:
    from backend.app.models.audit_job import AuditJob, FindingModel


class SubmitJobRequest(BaseModel):
    repo_url: str = Field(..., max_length=2048)
    repo_branch: Optional[str] = Field("main", max_length=255)

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        if not re.match(r"^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+(\.git)?$", v):
            raise ValueError("Only public GitHub HTTPS URLs are supported.")
        return v

    @field_validator("repo_branch")
    @classmethod
    def validate_repo_branch(cls, v: str | None) -> str:
        if v is None or not v.strip():
            return "main"

        branch = v.strip()
        if not re.match(r"^[a-zA-Z0-9._/-]+$", branch):
            raise ValueError("Invalid branch name format.")
        if branch.startswith(("-", "/")):
            raise ValueError("Branch name cannot start with a dash or slash.")
        if branch.endswith(("/", ".", ".lock")):
            raise ValueError("Branch name cannot end with a slash, dot, or .lock.")
        if ".." in branch or "//" in branch or "@{" in branch or "\\" in branch:
            raise ValueError("Branch name contains an unsafe ref sequence.")
        for component in branch.split("/"):
            if not component or component.startswith(".") or component.endswith(".lock"):
                raise ValueError("Branch name contains an unsafe path component.")
        return branch


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    repo_url: str
    repo_branch: str
    status: JobStatus
    created_at: str
    finished_at: Optional[str] = None
    cancel_requested: bool
    cancel_requested_at: Optional[str] = None
    report_pdf_url: Optional[str] = None
    error_message: Optional[str] = None


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_source: str
    title: str
    description: str
    severity: str
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    evidence: Optional[str] = None
    remediation: Optional[str] = None


class JobDetailResponse(BaseModel):
    job: JobResponse
    findings: List[FindingResponse]


def build_job_response(job: AuditJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        repo_url=job.repo_url,
        repo_branch=job.repo_branch,
        status=job.status,
        created_at=job.created_at.isoformat(),
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        cancel_requested=job.cancel_requested,
        cancel_requested_at=job.cancel_requested_at.isoformat() if job.cancel_requested_at else None,
        report_pdf_url=job.report_pdf_url,
        error_message=job.error_message,
    )


def build_finding_response(finding: FindingModel) -> FindingResponse:
    severity = finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
    return FindingResponse(
        id=finding.id,
        agent_source=finding.agent_source,
        title=finding.title,
        description=finding.description,
        severity=severity,
        cvss_score=finding.cvss_score,
        cvss_vector=finding.cvss_vector,
        evidence=finding.evidence,
        remediation=finding.remediation,
    )


def build_job_detail_response(job: AuditJob, findings: Sequence[FindingModel]) -> JobDetailResponse:
    return JobDetailResponse(
        job=build_job_response(job),
        findings=[build_finding_response(finding) for finding in findings],
    )
