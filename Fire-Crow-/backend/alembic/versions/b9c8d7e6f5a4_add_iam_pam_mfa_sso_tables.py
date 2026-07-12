"""add_iam_pam_mfa_sso_tables

Revision ID: b9c8d7e6f5a4
Revises: 33d7e9f3e8eb
Create Date: 2026-06-29 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "b9c8d7e6f5a4"
down_revision: Union[str, Sequence[str], None] = "33d7e9f3e8eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    from app.models import Base
    from app.models.mfa import MFAConfiguration, MFARecoveryCode, MFAAuditLog
    from app.models.sso import SSOProvider, SSOSession
    from app.models.pam import PrivilegedAccessRequest, PrivilegedAccessGrant, PrivilegedAccessAudit
    from app.models.iam import IAMPolicy, RolePermission, AccountAuditLog, ServiceAccount

    required_tables = [
        Base.metadata.tables["mfa_configurations"],
        Base.metadata.tables["mfa_recovery_codes"],
        Base.metadata.tables["mfa_audit_logs"],
        Base.metadata.tables["sso_providers"],
        Base.metadata.tables["sso_sessions"],
        Base.metadata.tables["privileged_access_requests"],
        Base.metadata.tables["privileged_access_grants"],
        Base.metadata.tables["privileged_access_audits"],
        Base.metadata.tables["iam_policies"],
        Base.metadata.tables["role_permissions"],
        Base.metadata.tables["account_audit_logs"],
        Base.metadata.tables["service_accounts"],
    ]
    Base.metadata.create_all(bind=bind, tables=required_tables, checkfirst=True)


def downgrade() -> None:
    tables_to_drop = [
        "mfa_configurations",
        "mfa_recovery_codes",
        "mfa_audit_logs",
        "sso_providers",
        "sso_sessions",
        "privileged_access_requests",
        "privileged_access_grants",
        "privileged_access_audits",
        "iam_policies",
        "role_permissions",
        "account_audit_logs",
        "service_accounts",
    ]
    for table in tables_to_drop:
        op.drop_table(table, if_exists=True)
