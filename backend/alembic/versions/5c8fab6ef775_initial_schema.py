"""Initial schema

Revision ID: 5c8fab6ef775
Revises: 
Create Date: 2026-06-07 03:13:57.686184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5c8fab6ef775'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _ensure_postgres_enum(enum_name: str, values: list[str]) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    values_sql = ", ".join(f"'{value}'" for value in values)
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                    CREATE TYPE {enum_name} AS ENUM ({values_sql});
                END IF;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    _ensure_postgres_enum("jobstatus", ["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "PARTIAL"])
    _ensure_postgres_enum("severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])

    jobstatus_enum = (
        postgresql.ENUM("QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "PARTIAL", name="jobstatus", create_type=False)
        if bind.dialect.name == "postgresql"
        else sa.Enum("QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "PARTIAL", name="jobstatus")
    )
    severity_enum = (
        postgresql.ENUM("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", name="severity", create_type=False)
        if bind.dialect.name == "postgresql"
        else sa.Enum("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", name="severity")
    )

    if not _table_exists(inspector, "audit_jobs"):
        op.create_table(
            "audit_jobs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=255), nullable=False),
            sa.Column("repo_url", sa.String(length=1024), nullable=False),
            sa.Column("repo_branch", sa.String(length=255), nullable=False),
            sa.Column("status", jobstatus_enum, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("cancel_requested", sa.Boolean(), nullable=False),
            sa.Column("cancel_requested_at", sa.DateTime(), nullable=True),
            sa.Column("report_pdf_url", sa.String(length=1024), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = inspect(bind)
    if not _index_exists(inspector, "audit_jobs", op.f("ix_audit_jobs_user_id")):
        op.create_index(op.f("ix_audit_jobs_user_id"), "audit_jobs", ["user_id"], unique=False)

    if not _table_exists(inspector, "roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("can_start_scans", sa.Boolean(), nullable=True),
            sa.Column("can_view_reports", sa.Boolean(), nullable=True),
            sa.Column("can_manage_users", sa.Boolean(), nullable=True),
            sa.Column("can_manage_billing", sa.Boolean(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = inspect(bind)
    if not _index_exists(inspector, "roles", op.f("ix_roles_name")):
        op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    if not _table_exists(inspector, "security_logs"):
        op.create_table(
            "security_logs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column("user_agent", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = inspect(bind)
    if not _index_exists(inspector, "security_logs", op.f("ix_security_logs_action")):
        op.create_index(op.f("ix_security_logs_action"), "security_logs", ["action"], unique=False)
    if not _index_exists(inspector, "security_logs", op.f("ix_security_logs_user_id")):
        op.create_index(op.f("ix_security_logs_user_id"), "security_logs", ["user_id"], unique=False)

    if not _table_exists(inspector, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=255), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("tenant_id", sa.String(length=255), nullable=True),
            sa.Column("role_id", sa.String(length=255), nullable=True),
            sa.Column("github_id", sa.String(length=255), nullable=True),
            sa.Column("google_id", sa.String(length=255), nullable=True),
            sa.Column("privacy_policy_version", sa.String(length=64), nullable=True),
            sa.Column("privacy_policy_accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("github_id"),
            sa.UniqueConstraint("google_id"),
        )
        inspector = inspect(bind)
    if not _index_exists(inspector, "users", op.f("ix_users_tenant_id")):
        op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)
    if not _index_exists(inspector, "users", op.f("ix_users_username")):
        op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    if not _table_exists(inspector, "agent_logs"):
        op.create_table(
            "agent_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("job_id", sa.String(length=36), nullable=False),
            sa.Column("agent_name", sa.String(length=100), nullable=False),
            sa.Column("log_level", sa.String(length=20), nullable=False),
            sa.Column("message", sa.String(), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["audit_jobs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = inspect(bind)
    if not _index_exists(inspector, "agent_logs", op.f("ix_agent_logs_job_id")):
        op.create_index(op.f("ix_agent_logs_job_id"), "agent_logs", ["job_id"], unique=False)

    if not _table_exists(inspector, "findings"):
        op.create_table(
            "findings",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("job_id", sa.String(length=36), nullable=False),
            sa.Column("agent_source", sa.String(length=100), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("severity", severity_enum, nullable=False),
            sa.Column("cvss_vector", sa.String(length=100), nullable=True),
            sa.Column("cvss_score", sa.Float(), nullable=True),
            sa.Column("evidence", sa.String(), nullable=True),
            sa.Column("remediation", sa.String(), nullable=True),
            sa.Column("cwe_id", sa.String(length=50), nullable=True),
            sa.Column("owasp_category", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["audit_jobs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = inspect(bind)
    if not _index_exists(inspector, "findings", op.f("ix_findings_job_id")):
        op.create_index(op.f("ix_findings_job_id"), "findings", ["job_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_findings_job_id'), table_name='findings')
    op.drop_table('findings')
    op.drop_index(op.f('ix_agent_logs_job_id'), table_name='agent_logs')
    op.drop_table('agent_logs')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_tenant_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_security_logs_user_id'), table_name='security_logs')
    op.drop_index(op.f('ix_security_logs_action'), table_name='security_logs')
    op.drop_table('security_logs')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_table('roles')
    op.drop_index(op.f('ix_audit_jobs_user_id'), table_name='audit_jobs')
    op.drop_table('audit_jobs')
    # ### end Alembic commands ###
