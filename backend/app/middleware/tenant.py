import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.graph.store import graph_store
from app.models.tenant import Tenant

logger = logging.getLogger("firecrow.middleware.tenant")

TENANT_SLUG_HEADER = "X-Tenant-Slug"


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id: Optional[str] = None
        tenant_slug = request.headers.get(TENANT_SLUG_HEADER)

        if tenant_slug:
            try:
                if settings.DATABASE_BACKEND == "neo4j":
                    tenant = graph_store.get_tenant_by_slug(tenant_slug)
                    if tenant:
                        tenant_id = tenant.id
                    else:
                        logger.warning("Tenant slug %s not found or inactive", tenant_slug)
                else:
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

        # FC-ISO-001: Tenant ID is derived ONLY from validated slug lookup or
        # from the authenticated user's context (set downstream by auth).
        # Raw X-Tenant-ID header is no longer trusted to prevent impersonation.

        request.state.tenant_id = tenant_id
        return await call_next(request)
