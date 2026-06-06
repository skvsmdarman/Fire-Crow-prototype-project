import os
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
from backend.app.models.database import Base, engine, get_db
from backend.app.api import auth_router, audit_router, sse_router, system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup step: Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Teardown step can go here (e.g., closing background pools)


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

    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal Server Error: {str(exc)}",
            "type": exc.__class__.__name__,
        }
    )

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
    db_error = ""
    try:
        # Verify database connection with a simple query
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False
        db_error = str(e)

    return {
        "status": "up",
        "database": "connected" if db_ok else f"error: {db_error}"
    }


frontend_dist_dir = Path(WORKSPACE_DIR) / "frontend" / "out"
if frontend_dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist_dir), html=True), name="frontend")
