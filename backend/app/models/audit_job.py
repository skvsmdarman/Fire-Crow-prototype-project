from sqlalchemy import String, DateTime, ForeignKey, Float, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.models.database import Base
from app.schemas.audit_state import JobStatus, Severity


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AuditJob(Base):
    __tablename__ = "audit_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    repo_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    repo_branch: Mapped[str] = mapped_column(String(255), default="main")
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(default=False, nullable=False)
    cancel_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_pdf_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    report_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    security_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    findings: Mapped[list["FindingModel"]] = relationship(
        "FindingModel", back_populates="job", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["AuditArtifact"]] = relationship(
        "AuditArtifact", back_populates="job", cascade="all, delete-orphan"
    )
    logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog", back_populates="job", cascade="all, delete-orphan"
    )
    phase_ledger: Mapped[list["PhaseLedgerModel"]] = relationship(
        "PhaseLedgerModel", back_populates="job", cascade="all, delete-orphan"
    )
    report_rel: Mapped[Optional["AuditReport"]] = relationship(
        "AuditReport",
        primaryjoin="AuditJob.id == AuditReport.job_id",
        uselist=False,
        cascade="all, delete-orphan",
        back_populates="job"
    )


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_jobs.id"), nullable=False, index=True)
    html_content: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    markdown_content: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="report_rel", foreign_keys=[job_id])


class FindingModel(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_jobs.id"), nullable=False, index=True)
    agent_source: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[Severity] = mapped_column(SQLEnum(Severity), nullable=False)
    cvss_vector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cvss_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    remediation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cwe_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    owasp_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scanner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scanner_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="findings")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_jobs.id"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    log_level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="logs")


class AuditArtifact(Base):
    __tablename__ = "audit_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_jobs.id"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    data_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="artifacts")


class PhaseLedgerModel(Base):
    __tablename__ = "phase_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_jobs.id"), nullable=False, index=True)
    phase_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # completed, failed, skipped, cancelled
    mode: Mapped[str] = mapped_column(String(50), nullable=False)  # real, simulated, degraded, skipped
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="phase_ledger")

