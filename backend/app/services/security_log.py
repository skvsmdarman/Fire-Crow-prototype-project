import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.security_log import SecurityLog
from app.models.user import User
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


def _anonymize_ip(ip: Optional[str], region: Optional[str], timezone_str: Optional[str] = None) -> Optional[str]:
    if not ip or ip in ("unknown", "localhost", "127.0.0.1", "::1"):
        return ip
        
    is_strict = False
    if region:
        reg_upper = region.upper()
        if reg_upper in ("IN", "INDIA", "EU", "EUROPE") or any(code in reg_upper for code in ("AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GB", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK")):
            is_strict = True
    if timezone_str:
        tz_lower = timezone_str.lower()
        if "kolkata" in tz_lower or "calcutta" in tz_lower or "europe" in tz_lower:
            is_strict = True
            
    if is_strict:
        if "." in ip:
            parts = ip.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        elif ":" in ip:
            parts = ip.split(":")
            if len(parts) > 3:
                return f"{parts[0]}:{parts[1]}:{parts[2]}::"
    return ip


def record_security_event(
    db: Session,
    *,
    action: str,
    request: Request,
    user_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    ip = get_client_ip(request)
    region = None
    timezone_str = None
    
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            region = user.region
            timezone_str = user.timezone

    anon_ip = _anonymize_ip(ip, region, timezone_str)
    serialized_details = safe_json_dumps(details, max_length=4096) if details else None
    
    db.add(
        SecurityLog(
            user_id=user_id,
            action=action,
            ip_address=anon_ip,
            user_agent=_safe_user_agent(request),
            details=serialized_details,
        )
    )
    db.commit()


def record_user_activity(
    db: Session,
    *,
    user_id: str,
    action: str,
    request: Request,
    details: Optional[dict[str, Any]] = None,
) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
        
    now = datetime.now(timezone.utc)
    ip = get_client_ip(request)
    anon_ip = _anonymize_ip(ip, user.region, user.timezone)
    
    entry: dict[str, Any] = {
        "action": action,
        "timestamp": now.isoformat(),
        "ip_masked": anon_ip != ip,
    }
    if details:
        entry["details"] = details
        
    try:
        history = json.loads(user.activity_log) if user.activity_log else []
    except Exception:
        history = []
        
    history.insert(0, entry)
    history = history[:50]
    user.activity_log = json.dumps(history)
    
    serialized_details = safe_json_dumps(details, max_length=4096) if details else None
    db.add(
        SecurityLog(
            user_id=user_id,
            action=action,
            ip_address=anon_ip,
            user_agent=_safe_user_agent(request),
            details=serialized_details,
        )
    )
    db.commit()
