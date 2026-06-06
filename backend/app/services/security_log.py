import json
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.models.security_log import SecurityLog


def get_client_ip(request: Request) -> Optional[str]:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else None


def record_security_event(
    db: Session,
    *,
    action: str,
    request: Request,
    user_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    serialized_details = json.dumps(details, separators=(",", ":"), ensure_ascii=True) if details else None
    db.add(
        SecurityLog(
            user_id=user_id,
            action=action,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            details=serialized_details,
        )
    )
    db.commit()
