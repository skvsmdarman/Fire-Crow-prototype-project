import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.models.tenant import Tenant

logger = logging.getLogger("firecrow.middleware.tenant")

TENANT_HEADER = "X-Tenant-ID"
TENANT_SLUG_HEADER = "X-Tenant-Slug"


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id: Optional[str] = None
        tenant_slug = request.headers.get(TENANT_SLUG_HEADER)

        if tenant_slug:
            try:
                from app.models.database import SessionLocal
                db = SessionLocal()
                try:
                    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug, Tenant.is_active == True).first()
                    if tenant:
                        tenant_id = tenant.id
                    else:
                        logger.warning("Tenant slug %s not found or inactive", tenant_slug)
                finally:
                    db.close()
            except Exception as e:
                logger.error("Tenant resolution failed for slug %s: %s", tenant_slug, e)

        if not tenant_id:
            tenant_id = request.headers.get(TENANT_HEADER)

        request.state.tenant_id = tenant_id
        return await call_next(request)
