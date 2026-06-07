import os
import logging
import uuid
from pathlib import Path
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from backend.app.services.limiter import limiter

from backend.app.config import settings, WORKSPACE_DIR
from backend.app.models.database import Base, engine, ensure_database_compatibility, get_db
from backend.app.api import auth_router, audit_router, sse_router, system_router
from backend.app.services.redaction import redact_text

logger = logging.getLogger("firecrow.main")


def _cors_origins() -> list[str]:
    origins: set[str] = set()
    if settings.FRONTEND_URL:
        origins.add(settings.FRONTEND_URL.rstrip("/"))
    if settings.CORS_ORIGINS:
        origins.update(origin.strip().rstrip("/") for origin in settings.CORS_ORIGINS.split(",") if origin.strip())
    if settings.DEBUG:
        origins.update(
            {
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3001",
            }
        )
    return sorted(origin for origin in origins if origin and origin != "*")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Compatibility only. Production deployments should run Alembic migrations before startup.
    if not settings.DEBUG:
        logger.warning("Running metadata create_all compatibility check; configure Alembic migrations for production.")
    Base.metadata.create_all(bind=engine)
    ensure_database_compatibility()
    
    # Startup check for pending migration problems
    try:
        from backend.app.models.database import check_pending_migrations
        if check_pending_migrations():
            logger.warning(
                "SECURITY WARNING: Pending database migrations detected. "
                "Please run 'alembic upgrade head' to ensure database schema is up-to-date."
            )
    except Exception as e:
        logger.error("Error running database migration startup check: %s", str(e))
        
    yield


app = FastAPI(
    title="Fire Crow API",
    description="Agentic Security Intelligence Platform Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
app.add_middleware(SlowAPIMiddleware)  # type: ignore


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Let FastAPI's default handler process HTTPException (400, 401, 404, etc.)
    from fastapi.exceptions import HTTPException as FastAPIHTTPException
    from starlette.exceptions import HTTPException as StarletteHTTPException
    if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
        raise exc

    error_id = str(uuid.uuid4())
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(
        "Unhandled request error error_id=%s request_id=%s method=%s path=%s",
        error_id,
        request_id,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data: https://fonts.gstatic.com https://fonts.googleapis.com; "
        "img-src 'self' data: https://avatars.githubusercontent.com https://*.googleusercontent.com https://*; "
        "connect-src 'self' ws: wss: http: https:;"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Register API Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(sse_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")

# Ensure reports directory exists for authenticated downloads
reports_dir = os.path.join(WORKSPACE_DIR, "workspace", "reports")
os.makedirs(reports_dir, exist_ok=True)


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Verify database connection with a simple query
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
        logger.warning("Health check database probe failed.", exc_info=True)

    return {
        "status": "up" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable"
    }


frontend_dist_dir = Path(WORKSPACE_DIR) / "frontend" / "out"
if frontend_dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist_dir), html=True), name="frontend")
