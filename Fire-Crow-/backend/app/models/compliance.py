from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.models.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    country_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_residency_preference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(255), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )


class DataProcessingRecord(Base):
    __tablename__ = "data_processing_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    data_category: Mapped[str] = mapped_column(String(100), nullable=False)
    processing_purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    processing_basis: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    retention_policy_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    @property
    def tenant_id(self) -> str:
        return self.organization_id

    @tenant_id.setter
    def tenant_id(self, value: str):
        self.organization_id = value


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_category: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    delete_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="hard_delete")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )


class ArtifactObject(Base):
    __tablename__ = "artifact_objects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    finding_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(100), nullable=False, default="cloudflare_r2")
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sensitivity_level: Mapped[str] = mapped_column(String(50), nullable=False, default="internal")
    encryption_status: Mapped[str] = mapped_column(String(100), nullable=False, default="encrypted_at_rest")
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    retention_policy_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    delete_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deletion_status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    @property
    def tenant_id(self) -> str:
        return self.organization_id

    @tenant_id.setter
    def tenant_id(self, value: str):
        self.organization_id = value


class ComplianceEvent(Base):
    __tablename__ = "compliance_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    data_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    object_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def tenant_id(self) -> Optional[str]:
        return self.organization_id

    @tenant_id.setter
    def tenant_id(self, value: Optional[str]):
        self.organization_id = value


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    requester_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result_artifact_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @property
    def tenant_id(self) -> str:
        return self.organization_id

    @tenant_id.setter
    def tenant_id(self, value: str):
        self.organization_id = value


class AuthorizationAttestation(Base):
    __tablename__ = "authorization_attestations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    repo_url_normalized: Mapped[str] = mapped_column(String(1024), nullable=False)
    repo_owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    authorization_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    attestation_text_version: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    @property
    def tenant_id(self) -> str:
        return self.organization_id

    @tenant_id.setter
    def tenant_id(self, value: str):
        self.organization_id = value


class SecretRedactionEvent(Base):
    __tablename__ = "secret_redaction_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_jobs.id"), nullable=False, index=True)
    finding_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    redaction_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_token: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def tenant_id(self) -> str:
        return self.organization_id

    @tenant_id.setter
    def tenant_id(self, value: str):
        self.organization_id = value
