# Import routers for FastAPI app

from app.api.routes_auth import router as auth_router
from app.api.routes_audit import router as audit_router
from app.api.routes_sse import router as sse_router
from app.api.routes_system import router as system_router
from app.api.routes_storage import router as storage_router
from app.api.routes_chat import router as chat_router
from app.api.routes_leaderboard import router as leaderboard_router
from app.api.routes_push import router as push_router
from app.api.routes_user import router as user_router
from app.api.routes_mfa import router as mfa_router
from app.api.routes_sso import router as sso_router
from app.api.routes_pam import router as pam_router
from app.api.routes_iam import router as iam_router
from app.api.routes_tenant import router as tenant_router


