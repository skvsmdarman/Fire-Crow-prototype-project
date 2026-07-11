"""add_credit_score_and_push_subscriptions

Revision ID: f47ac10b58cc
Revises: 3a3e549bf3a8
Create Date: 2026-06-09 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f47ac10b58cc'
down_revision: Union[str, Sequence[str], None] = '3a3e549bf3a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add credit_balance to users
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "credit_balance" not in columns:
            op.add_column('users', sa.Column('credit_balance', sa.Float(), nullable=False, server_default='10.0'))

    # Add security_score to audit_jobs
    if "audit_jobs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("audit_jobs")}
        if "security_score" not in columns:
            op.add_column('audit_jobs', sa.Column('security_score', sa.Float(), nullable=True))

    # Create push_subscriptions if missing
    if "push_subscriptions" not in inspector.get_table_names():
        op.create_table(
            'push_subscriptions',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=255), nullable=False),
            sa.Column('endpoint', sa.Text(), nullable=False),
            sa.Column('p256dh', sa.String(length=255), nullable=False),
            sa.Column('auth', sa.String(length=255), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_push_subscriptions_user_id'), 'push_subscriptions', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "push_subscriptions" in inspector.get_table_names():
        op.drop_index(op.f('ix_push_subscriptions_user_id'), table_name='push_subscriptions')
        op.drop_table('push_subscriptions')

    if "audit_jobs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("audit_jobs")}
        if "security_score" in columns:
            op.drop_column('audit_jobs', 'security_score')

    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "credit_balance" in columns:
            op.drop_column('users', 'credit_balance')
