"""add_auth_exchange_codes

Revision ID: d8a7f2b0c1aa
Revises: e3937218d940
Create Date: 2026-06-07 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "d8a7f2b0c1aa"
down_revision: Union[str, Sequence[str], None] = "e3937218d940"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector, "auth_exchange_codes"):
        op.create_table(
            "auth_exchange_codes",
            sa.Column("code", sa.String(length=255), nullable=False),
            sa.Column("user_id", sa.String(length=255), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("access_token", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("code"),
        )
        inspector = inspect(bind)

    if not _index_exists(inspector, "auth_exchange_codes", op.f("ix_auth_exchange_codes_user_id")):
        op.create_index(op.f("ix_auth_exchange_codes_user_id"), "auth_exchange_codes", ["user_id"], unique=False)
    if not _index_exists(inspector, "auth_exchange_codes", op.f("ix_auth_exchange_codes_expires_at")):
        op.create_index(op.f("ix_auth_exchange_codes_expires_at"), "auth_exchange_codes", ["expires_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if _table_exists(inspector, "auth_exchange_codes"):
        if _index_exists(inspector, "auth_exchange_codes", op.f("ix_auth_exchange_codes_expires_at")):
            op.drop_index(op.f("ix_auth_exchange_codes_expires_at"), table_name="auth_exchange_codes")
        if _index_exists(inspector, "auth_exchange_codes", op.f("ix_auth_exchange_codes_user_id")):
            op.drop_index(op.f("ix_auth_exchange_codes_user_id"), table_name="auth_exchange_codes")
        op.drop_table("auth_exchange_codes")
