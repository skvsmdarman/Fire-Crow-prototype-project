from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.user import UserActivityEvent
from app.services.redaction import safe_json_dumps


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def append_user_activity(
    db: Session,
    *,
    user_id: str,
    action: str,
    details: Optional[dict[str, Any]] = None,
) -> UserActivityEvent:
    event = UserActivityEvent(
        user_id=user_id,
        action=action,
        details_json=safe_json_dumps(details, max_length=4096) if details else None,
        created_at=_utc_now(),
    )
    db.add(event)
    return event


def list_user_activities(
    db: Session,
    *,
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = (
        db.query(UserActivityEvent)
        .filter(UserActivityEvent.user_id == user_id)
        .order_by(UserActivityEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    activities: list[dict[str, Any]] = []
    for row in rows:
        activity: dict[str, Any] = {
            "action": row.action,
            "timestamp": row.created_at.isoformat(),
        }
        if row.details_json:
            try:
                activity["details"] = json.loads(row.details_json)
            except json.JSONDecodeError:
                activity["details"] = {"raw": row.details_json}
        activities.append(activity)
    return activities


def delete_user_activities(db: Session, *, user_id: str) -> int:
    return (
        db.query(UserActivityEvent)
        .filter(UserActivityEvent.user_id == user_id)
        .delete(synchronize_session=False)
    )
