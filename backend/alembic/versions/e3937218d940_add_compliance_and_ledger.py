"""add_compliance_and_ledger

Revision ID: e3937218d940
Revises: ce1b119cf0fd
Create Date: 2026-06-07 20:45:21.688827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'e3937218d940'
down_revision: Union[str, Sequence[str], None] = 'ce1b119cf0fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if _table_exists(inspector, "audit_jobs") and not _column_exists(inspector, "audit_jobs", "tenant_id"):
        op.add_column("audit_jobs", sa.Column("tenant_id", sa.String(length=255), nullable=True))
        inspector = inspect(bind)
    if _table_exists(inspector, "audit_jobs") and not _index_exists(inspector, "audit_jobs", op.f("ix_audit_jobs_tenant_id")):
        op.create_index(op.f("ix_audit_jobs_tenant_id"), "audit_jobs", ["tenant_id"], unique=False)

    from backend.app.models import Base
    from backend.app.models.compliance import (
        ArtifactObject,
        AuthorizationAttestation,
        ComplianceEvent,
        DataProcessingRecord,
        Membership,
        Organization,
        PrivacyRequest,
        RetentionPolicy,
        SecretRedactionEvent,
    )
    from backend.app.models.user import LoginFailure, UserSession
    from backend.app.models.audit_job import PhaseLedgerModel

    required_tables = [
        Base.metadata.tables["organizations"],
        Base.metadata.tables["memberships"],
        Base.metadata.tables["data_processing_records"],
        Base.metadata.tables["retention_policies"],
        Base.metadata.tables["artifact_objects"],
        Base.metadata.tables["compliance_events"],
        Base.metadata.tables["privacy_requests"],
        Base.metadata.tables["authorization_attestations"],
        Base.metadata.tables["secret_redaction_events"],
        Base.metadata.tables["login_failures"],
        Base.metadata.tables["user_sessions"],
        Base.metadata.tables["phase_ledger"],
    ]
    Base.metadata.create_all(bind=bind, tables=required_tables, checkfirst=True)

    inspector = inspect(bind)
    if _table_exists(inspector, "users"):
        if bind.dialect.name == "postgresql":
            op.execute(
                sa.text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower_unique
                    ON users (lower(email))
                    WHERE email IS NOT NULL
                    """
                )
            )
        elif bind.dialect.name == "sqlite":
            op.execute(
                sa.text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower_unique
                    ON users (lower(email))
                    WHERE email IS NOT NULL
                    """
                )
            )


def downgrade() -> None:
    """Downgrade schema."""
    pass
