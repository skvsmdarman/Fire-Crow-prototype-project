"""normalize user activity events

Revision ID: 4f0f2d3c1b7a
Revises: 187c538a7649
Create Date: 2026-07-06 00:00:00.000000
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "4f0f2d3c1b7a"
down_revision = "187c538a7649"
branch_labels = None
depends_on = None


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        return datetime.now(timezone.utc)
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return datetime.now(timezone.utc)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "user_activity_events" not in tables:
        op.create_table(
            "user_activity_events",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                sa.String(length=255),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_user_activity_events_user_id", "user_activity_events", ["user_id"])
        op.create_index("ix_user_activity_events_action", "user_activity_events", ["action"])
        op.create_index("ix_user_activity_events_created_at", "user_activity_events", ["created_at"])

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "activity_log" in user_columns:
        users = bind.execute(sa.text("SELECT id, activity_log FROM users WHERE activity_log IS NOT NULL")).fetchall()
        for row in users:
            user_id = row[0]
            raw_log = row[1]
            try:
                entries = json.loads(raw_log)
            except (TypeError, json.JSONDecodeError):
                entries = []
            if not isinstance(entries, list):
                entries = []
            for item in entries:
                if not isinstance(item, dict):
                    continue
                action = str(item.get("action") or "activity")
                details: dict[str, Any] = {}
                nested_details = item.get("details")
                if isinstance(nested_details, dict):
                    details.update(nested_details)
                for key, value in item.items():
                    if key in {"action", "timestamp", "details"}:
                        continue
                    details[key] = value
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO user_activity_events (id, user_id, action, details_json, created_at)
                        VALUES (:id, :user_id, :action, :details_json, :created_at)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "action": action[:100],
                        "details_json": json.dumps(details) if details else None,
                        "created_at": _parse_timestamp(item.get("timestamp")),
                    },
                )
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("activity_log")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "activity_log" not in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("activity_log", sa.Text(), nullable=True))

    user_ids = [row[0] for row in bind.execute(sa.text("SELECT DISTINCT user_id FROM user_activity_events")).fetchall()]
    for user_id in user_ids:
        rows = bind.execute(
            sa.text(
                """
                SELECT action, details_json, created_at
                FROM user_activity_events
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                """
            ),
            {"user_id": user_id},
        ).fetchall()
        entries = []
        for action, details_json, created_at in rows:
            entry: dict[str, Any] = {
                "action": action,
                "timestamp": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
            }
            if details_json:
                try:
                    details = json.loads(details_json)
                except json.JSONDecodeError:
                    details = {"raw": details_json}
                entry["details"] = details
            entries.append(entry)
        bind.execute(
            sa.text("UPDATE users SET activity_log = :activity_log WHERE id = :user_id"),
            {"user_id": user_id, "activity_log": json.dumps(entries)},
        )

    op.drop_index("ix_user_activity_events_created_at", table_name="user_activity_events")
    op.drop_index("ix_user_activity_events_action", table_name="user_activity_events")
    op.drop_index("ix_user_activity_events_user_id", table_name="user_activity_events")
    op.drop_table("user_activity_events")
