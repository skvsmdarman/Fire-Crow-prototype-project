import os
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

# Try to import slowapi for rate limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    from slowapi.middleware import SlowAPIMiddleware  # type: ignore
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    limiter = None
    _rate_limit_exceeded_handler = None
    RateLimitExceeded = None
    SlowAPIMiddleware = None

from backend.app.config import settings, WORKSPACE_DIR
from backend.app.models.database import Base, engine, get_db
from backend.app.api import auth_router, audit_router, sse_router, system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup step: Create database tables in debug mode
    if settings.DEBUG:
        Base.metadata.create_all(bind=engine)
    yield
    # Teardown step can go here (e.g., closing background pools)


app = FastAPI(
    title="Fire Crow API",
    description="Agentic Security Intelligence Platform Backend",
    version="1.0.0",
    lifespan=lifespan
)

if SLOWAPI_AVAILABLE:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
    app.add_middleware(SlowAPIMiddleware)  # type: ignore

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL] if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
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


@app.get("/")
async def root():
    return {
        "name": "Fire Crow API",
        "status": "healthy",
        "version": "1.0.0",
        "debug_mode": settings.DEBUG
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    db_error = ""
    try:
        # Verify database connection
        db.execute(Base.metadata.tables["audit_jobs"].select().limit(1))
        db_ok = True
    except Exception as e:
        db_ok = False
        db_error = str(e)

    return {
        "status": "up",
        "database": "connected" if db_ok else f"error: {db_error}"
    }
