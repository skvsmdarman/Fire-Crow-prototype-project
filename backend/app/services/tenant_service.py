from __future__ import annotations

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.tenant import Tenant
from app.models.user import User
from app.models.audit_job import AuditJob

logger = logging.getLogger("firecrow.services.tenant")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_tenant(
    db: Session,
    name: str,
    slug: str,
    domain: Optional[str] = None,
    plan: str = "free",
    max_users: Optional[int] = None,
    max_storage_gb: Optional[int] = None,
) -> Tenant:
    existing = db.query(Tenant).filter(
        (Tenant.slug == slug) | (Tenant.domain == domain) if domain else (Tenant.slug == slug)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tenant slug or domain already exists.")

    tenant = Tenant(
        name=name,
        slug=slug,
        domain=domain,
        plan=plan,
        max_users=max_users,
        max_storage_gb=max_storage_gb,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def get_tenant(tenant_id: str, db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    return tenant


def get_tenant_by_slug(slug: str, db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.slug == slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    return tenant


def list_tenants(db: Session, active_only: bool = False) -> list[Tenant]:
    query = db.query(Tenant)
    if active_only:
        query = query.filter(Tenant.is_active == True)
    return query.order_by(Tenant.created_at.desc()).all()


def update_tenant(tenant_id: str, db: Session, **kwargs) -> Tenant:
    tenant = get_tenant(tenant_id, db)
    for key, value in kwargs.items():
        if value is not None and hasattr(tenant, key):
            setattr(tenant, key, value)
    tenant.updated_at = _utc_now()
    db.commit()
    db.refresh(tenant)
    return tenant


def deactivate_tenant(tenant_id: str, db: Session) -> Tenant:
    tenant = get_tenant(tenant_id, db)
    tenant.is_active = False
    tenant.updated_at = _utc_now()
    db.commit()
    db.refresh(tenant)
    return tenant


def get_tenant_stats(tenant_id: str, db: Session) -> dict:
    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar() or 0
    active_jobs = db.query(func.count(AuditJob.id)).filter(
        AuditJob.tenant_id == tenant_id,
        AuditJob.status.in_(["queued", "running"]),
    ).scalar() or 0
    total_jobs = db.query(func.count(AuditJob.id)).filter(AuditJob.tenant_id == tenant_id).scalar() or 0

    tenant = get_tenant(tenant_id, db)
    return {
        "tenant_id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "is_active": tenant.is_active,
        "user_count": user_count,
        "active_jobs": active_jobs,
        "total_jobs": total_jobs,
        "max_users": tenant.max_users,
        "max_storage_gb": tenant.max_storage_gb,
    }


def resolve_tenant_from_request(request: Request, db: Session) -> Optional[Tenant]:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        return None
    return get_tenant(tenant_id, db)


def tenant_to_dict(tenant: Tenant) -> dict:
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "domain": tenant.domain,
        "plan": tenant.plan,
        "is_active": tenant.is_active,
        "max_users": tenant.max_users,
        "max_storage_gb": tenant.max_storage_gb,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
    }
