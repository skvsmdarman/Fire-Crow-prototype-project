from __future__ import annotations

import json
import logging
import secrets
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.iam import IAMPolicy, RolePermission, AccountAuditLog, ServiceAccount
from app.models.user import User
from app.models.role import Role
from app.models.mfa import MFAConfiguration
from app.models.pam import PrivilegedAccessGrant
from app.models.sso import SSOSession
from app.services.security_log import record_security_event

logger = logging.getLogger("firecrow.services.iam")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def check_permission(user: User, permission: str, resource: str = "*", db: Optional[Session] = None) -> bool:
    if user.is_admin:
        return True

    if user.role_id:
        role_perm = db.query(RolePermission).filter(
            RolePermission.role_id == user.role_id,
            RolePermission.permission == permission,
        ).first() if db else None
        if role_perm:
            return _resource_matches(role_perm.resource_pattern, resource)

    if db:
        active_grant = db.query(PrivilegedAccessGrant).filter(
            PrivilegedAccessGrant.user_id == user.id,
            PrivilegedAccessGrant.permission == permission,
            PrivilegedAccessGrant.is_active == True,
            PrivilegedAccessGrant.expires_at > _utc_now(),
        ).first()
        if active_grant:
            return True

    return False


def _resource_matches(pattern: str, resource: str) -> bool:
    if pattern == "*":
        return True
    import fnmatch
    return fnmatch.fnmatch(resource, pattern)


def enforce_least_privilege(user_id: str, required_permission: str, resource: str = "*",
                            db: Optional[Session] = None) -> bool:
    user = db.query(User).filter(User.id == user_id).first() if db else None
    if not user:
        return False
    return check_permission(user, required_permission, resource, db)


def create_iam_policy(
    db: Session,
    name: str,
    effect: str,
    actions: list[str],
    resources: list[str],
    description: Optional[str] = None,
    conditions: Optional[str] = None,
    priority: int = 0,
) -> IAMPolicy:
    existing = db.query(IAMPolicy).filter(IAMPolicy.name == name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"IAM Policy '{name}' already exists.")

    policy = IAMPolicy(
        name=name,
        description=description,
        effect=effect,
        actions=",".join(actions),
        resources=",".join(resources),
        conditions=conditions,
        priority=priority,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def delete_iam_policy(policy_id: str, db: Session) -> None:
    policy = db.query(IAMPolicy).filter(IAMPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="IAM Policy not found.")
    if policy.is_system:
        raise HTTPException(status_code=403, detail="System policies cannot be deleted.")
    db.delete(policy)
    db.commit()


def assign_role_permission(
    db: Session,
    role_id: str,
    permission: str,
    resource_pattern: str = "*",
) -> RolePermission:
    rp = RolePermission(
        role_id=role_id,
        permission=permission,
        resource_pattern=resource_pattern,
    )
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return rp


def remove_role_permission(permission_id: str, db: Session) -> None:
    rp = db.query(RolePermission).filter(RolePermission.id == permission_id).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Role permission not found.")
    db.delete(rp)
    db.commit()


def get_role_permissions(role_id: str, db: Session) -> list[RolePermission]:
    return db.query(RolePermission).filter(RolePermission.role_id == role_id).all()


def get_all_iam_policies(db: Session) -> list[IAMPolicy]:
    return db.query(IAMPolicy).order_by(IAMPolicy.priority.desc()).all()


def deactivate_user(user_id: str, db: Session, triggered_by: Optional[str] = None, reason: Optional[str] = None) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    db.commit()
    db.refresh(user)

    _record_account_audit(db, user_id=user_id, action="user.deactivated",
                          triggered_by=triggered_by,
                          details={"reason": reason})
    return user


def reactivate_user(user_id: str, db: Session, triggered_by: Optional[str] = None) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    db.commit()
    db.refresh(user)

    _record_account_audit(db, user_id=user_id, action="user.reactivated",
                          triggered_by=triggered_by)
    return user


def delete_user_permanently(user_id: str, db: Session, triggered_by: Optional[str] = None) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    db.query(PrivilegedAccessGrant).filter(PrivilegedAccessGrant.user_id == user_id).delete()
    db.query(SSOSession).filter(SSOSession.user_id == user_id).delete()
    db.query(MFAConfiguration).filter(MFAConfiguration.user_id == user_id).delete()
    db.delete(user)
    db.commit()

    _record_account_audit(db, user_id=user_id, action="user.permanently_deleted",
                          triggered_by=triggered_by)


def find_dormant_users(db: Session, days_threshold: int = 90) -> list[dict]:
    cutoff = _utc_now() - timedelta(days=days_threshold)
    dormant = db.query(User).filter(
        User.is_active == True,
        User.last_login_at < cutoff,
    ).all()

    results = []
    for user in dormant:
        results.append({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
            "days_since_login": (cutoff - user.last_login_at).days if user.last_login_at else days_threshold,
        })
    return results


def detect_shared_accounts(db: Session, threshold_ips: int = 5) -> list[dict]:
    from app.models.user import UserSession
    suspicious = (
        db.query(
            UserSession.user_id,
            User,
            func.count(func.distinct(UserSession.ip_hash)).label("unique_ips"),
        )
        .join(User, User.id == UserSession.user_id)
        .filter(
            User.is_active == True,
            UserSession.created_at > (_utc_now() - timedelta(days=30)),
        )
        .group_by(UserSession.user_id, User.id)
        .having(func.count(func.distinct(UserSession.ip_hash)) >= threshold_ips)
        .all()
    )

    results = []
    for _, user, unique_ips in suspicious:
        results.append({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "distinct_ip_addresses_30d": unique_ips,
        })
    return results


def create_service_account(
    db: Session,
    name: str,
    owner_id: str,
    permissions: list[str],
    description: Optional[str] = None,
    expires_in_days: Optional[int] = None,
) -> dict:
    existing = db.query(ServiceAccount).filter(ServiceAccount.name == name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Service account '{name}' already exists.")

    token = f"fc_svc_{secrets.token_urlsafe(32)}"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    token_prefix = token[:20]

    expires_at = None
    if expires_in_days:
        expires_at = _utc_now() + timedelta(days=expires_in_days)

    svc = ServiceAccount(
        name=name,
        description=description,
        owner_id=owner_id,
        token_hash=token_hash,
        token_prefix=token_prefix,
        permissions=",".join(permissions),
        expires_at=expires_at,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)

    _record_account_audit(db, user_id=owner_id, action="service_account.created",
                          details={"service_account_name": name, "permissions": permissions})

    return {
        "id": svc.id,
        "name": svc.name,
        "token": token,
        "token_prefix": token_prefix,
        "permissions": permissions,
        "expires_at": svc.expires_at.isoformat() if svc.expires_at else None,
    }


def revoke_service_account(account_id: str, db: Session) -> None:
    svc = db.query(ServiceAccount).filter(ServiceAccount.id == account_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service account not found.")
    svc.is_active = False
    db.commit()

    _record_account_audit(db, user_id=svc.owner_id, action="service_account.revoked",
                          details={"service_account_name": svc.name})


def verify_service_account_token(token: str, db: Session) -> Optional[ServiceAccount]:
    if not token.startswith("fc_svc_"):
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    svc = db.query(ServiceAccount).filter(
        ServiceAccount.token_hash == token_hash,
        ServiceAccount.is_active == True,
    ).first()
    if not svc:
        return None
    if svc.expires_at and svc.expires_at < _utc_now():
        return None
    svc.last_used_at = _utc_now()
    db.commit()
    return svc


def run_account_cleanup(db: Session, dormant_days: int = 90) -> dict:
    stats = {"deactivated": 0, "grants_expired": 0, "notified": 0}

    from app.services.pam_service import expire_stale_grants
    stats["grants_expired"] = expire_stale_grants(db)

    cutoff = _utc_now() - timedelta(days=dormant_days)
    dormant_users = db.query(User).filter(
        User.is_active == True,
        User.last_login_at < cutoff,
    ).all()

    for user in dormant_users:
        user.is_active = False
        _record_account_audit(db, user_id=user.id, action="user.auto_deactivated",
                              details={"reason": f"Dormant for >{dormant_days} days"})
        stats["deactivated"] += 1

    if dormant_users:
        db.commit()

    return stats


def _record_account_audit(
    db: Session,
    user_id: str,
    action: str,
    triggered_by: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    db.add(AccountAuditLog(
        user_id=user_id,
        action=action,
        triggered_by=triggered_by,
        details=json.dumps(details) if details else None,
    ))


def policy_to_dict(policy: IAMPolicy) -> dict:
    return {
        "id": policy.id,
        "name": policy.name,
        "description": policy.description,
        "effect": policy.effect,
        "actions": policy.actions.split(","),
        "resources": policy.resources.split(","),
        "conditions": policy.conditions,
        "priority": policy.priority,
        "is_system": policy.is_system,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


def role_permission_to_dict(rp: RolePermission) -> dict:
    return {
        "id": rp.id,
        "role_id": rp.role_id,
        "permission": rp.permission,
        "resource_pattern": rp.resource_pattern,
    }
