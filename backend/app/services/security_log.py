from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.security_log import SecurityLog
from app.services.redaction import safe_json_dumps


def get_client_ip(request: Request) -> Optional[str]:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else None


def _safe_user_agent(request: Request) -> Optional[str]:
    user_agent = request.headers.get("user-agent")
    return user_agent[:512] if user_agent else None


def record_security_event(
    db: Session,
    *,
    action: str,
    request: Request,
    user_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    serialized_details = safe_json_dumps(details, max_length=4096) if details else None
    db.add(
        SecurityLog(
            user_id=user_id,
            action=action,
            ip_address=get_client_ip(request),
            user_agent=_safe_user_agent(request),
            details=serialized_details,
        )
    )
    db.commit()
