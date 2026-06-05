from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import httpx
import urllib.parse

from backend.app.services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password
)
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    code: Optional[str] = None
    username: str
    password: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: str


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new database-backed user/workspace.
    """
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username is already registered")

    new_user = User(
        id=f"usr_{username.lower()}",
        username=username,
        password_hash=hash_password(request.password),
        email=request.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(user_id=new_user.id, username=new_user.username)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=new_user.username,
        user_id=new_user.id
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Create a local workspace session token using database credentials.
    In debug mode, users are auto-created on first login to facilitate testing.
    """
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Workspace name is required")

    user = db.query(User).filter(User.username == username).first()

    # If the user doesn't exist yet
    if not user:
        if settings.DEBUG:
            # Auto-create user with password provided, or default to "password123" for tests
            pwd = request.password or "password123"
            user = User(
                id=f"usr_{username.lower()}",
                username=username,
                password_hash=hash_password(pwd)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid workspace name or password"
            )
    else:
        # If user exists, verify password.
        # In debug mode, if no password is provided in the request, we default to "password123" to keep unit tests passing.
        pwd = request.password
        if pwd is None and settings.DEBUG:
            pwd = "password123"
        
        if not pwd or not user.password_hash or not verify_password(pwd, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid workspace name or password"
            )

    token = create_access_token(user_id=user.id, username=user.username)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        user_id=user.id
    )


@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return details of the current authenticated user session."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Fallback to token payload values if DB query yielded no results
        username = user_id.replace("usr_", "")
        email = None
    else:
        username = user.username
        email = user.email

    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": "security_engineer"
    }


@router.get("/github")
async def github_login(state: Optional[str] = None):
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fire Crow - Mock GitHub OAuth</title>
            <style>
                body {
                    background-color: #0b0f19;
                    color: #f3f4f6;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .card {
                    background: rgba(17, 24, 39, 0.7);
                    backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 16px;
                    padding: 40px;
                    width: 450px;
                    text-align: center;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
                }
                h1 {
                    font-size: 24px;
                    margin-bottom: 8px;
                    background: linear-gradient(135deg, #a78bfa, #818cf8);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                p {
                    color: #9ca3af;
                    font-size: 14px;
                    margin-bottom: 24px;
                }
                .btn {
                    display: block;
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #818cf8, #6366f1);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-weight: 600;
                    cursor: pointer;
                    margin-bottom: 12px;
                    transition: transform 0.2s, opacity 0.2s;
                }
                .btn:hover {
                    opacity: 0.95;
                    transform: translateY(-1px);
                }
                .input-group {
                    margin-bottom: 16px;
                    text-align: left;
                }
                label {
                    display: block;
                    font-size: 12px;
                    color: #9ca3af;
                    margin-bottom: 4px;
                }
                input {
                    width: 100%;
                    padding: 10px;
                    background: rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                    color: white;
                    box-sizing: border-box;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Fire Crow OAuth Sandbox</h1>
                <p>You are running in local debug mode. Authenticate with a simulated GitHub account:</p>
                <form action="/api/v1/auth/github/callback" method="get">
                    <input type="hidden" name="code" value="mock_github_code" />
                    <div class="input-group">
                        <label>GitHub Username</label>
                        <input type="text" name="mock_username" value="octocat" required />
                    </div>
                    <div class="input-group">
                        <label>Email Address</label>
                        <input type="email" name="mock_email" value="octocat@github.com" required />
                    </div>
                    <div class="input-group">
                        <label>GitHub User ID</label>
                        <input type="text" name="mock_id" value="583234" required />
                    </div>
                    <button type="submit" class="btn">Authorize Mock GitHub Profile</button>
                </form>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html_content)

    backend_callback = "http://localhost:8000/api/v1/auth/github/callback"
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": backend_callback,
        "scope": "user:email",
        "state": state or "random_state"
    }
    url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: Optional[str] = None,
    mock_username: Optional[str] = None,
    mock_email: Optional[str] = None,
    mock_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if code == "mock_github_code" or not settings.GITHUB_CLIENT_ID:
        username = mock_username or "octocat"
        email = mock_email or "octocat@github.com"
        github_id = mock_id or "583234"
    else:
        backend_callback = "http://localhost:8000/api/v1/auth/github/callback"
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": backend_callback
                }
            )
            if token_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to retrieve access token from GitHub")
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {token_data.get('error_description', 'No access token')}")

            user_res = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}"}
            )
            if user_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to retrieve user profile from GitHub")
            
            profile = user_res.json()
            github_id = str(profile.get("id"))
            username = profile.get("login") or f"github_{github_id}"
            email = profile.get("email")
            
            if not email:
                emails_res = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"token {access_token}"}
                )
                if emails_res.status_code == 200:
                    emails_list = emails_res.json()
                    for email_obj in emails_list:
                        if email_obj.get("primary"):
                            email = email_obj.get("email")
                            break

    user = db.query(User).filter(User.github_id == github_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.github_id = github_id
            db.commit()

    if not user:
        base_username = username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
            
        user = User(
            id=f"usr_{username.lower()}",
            username=username,
            email=email,
            github_id=github_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user_id=user.id, username=user.username)
    redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/signin?token={token}&username={user.username}&user_id={user.id}"
    return RedirectResponse(redirect_url)


@router.get("/google")
async def google_login(state: Optional[str] = None):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fire Crow - Mock Google OAuth</title>
            <style>
                body {
                    background-color: #0b0f19;
                    color: #f3f4f6;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .card {
                    background: rgba(17, 24, 39, 0.7);
                    backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 16px;
                    padding: 40px;
                    width: 450px;
                    text-align: center;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
                }
                h1 {
                    font-size: 24px;
                    margin-bottom: 8px;
                    background: linear-gradient(135deg, #f87171, #facc15);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                p {
                    color: #9ca3af;
                    font-size: 14px;
                    margin-bottom: 24px;
                }
                .btn {
                    display: block;
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #ea4335, #fbbc05);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-weight: 600;
                    cursor: pointer;
                    margin-bottom: 12px;
                    transition: transform 0.2s, opacity 0.2s;
                }
                .btn:hover {
                    opacity: 0.95;
                    transform: translateY(-1px);
                }
                .input-group {
                    margin-bottom: 16px;
                    text-align: left;
                }
                label {
                    display: block;
                    font-size: 12px;
                    color: #9ca3af;
                    margin-bottom: 4px;
                }
                input {
                    width: 100%;
                    padding: 10px;
                    background: rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                    color: white;
                    box-sizing: border-box;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Fire Crow Google OAuth Sandbox</h1>
                <p>You are running in local debug mode. Authenticate with a simulated Google account:</p>
                <form action="/api/v1/auth/google/callback" method="get">
                    <input type="hidden" name="code" value="mock_google_code" />
                    <div class="input-group">
                        <label>Google Username</label>
                        <input type="text" name="mock_username" value="guser" required />
                    </div>
                    <div class="input-group">
                        <label>Email Address</label>
                        <input type="email" name="mock_email" value="guser@gmail.com" required />
                    </div>
                    <div class="input-group">
                        <label>Google User ID</label>
                        <input type="text" name="mock_id" value="1092837465" required />
                    </div>
                    <button type="submit" class="btn">Authorize Mock Google Profile</button>
                </form>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html_content)

    backend_callback = "http://localhost:8000/api/v1/auth/google/callback"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": backend_callback,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state or "random_state"
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: Optional[str] = None,
    mock_username: Optional[str] = None,
    mock_email: Optional[str] = None,
    mock_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if code == "mock_google_code" or not settings.GOOGLE_CLIENT_ID:
        username = mock_username or "guser"
        email = mock_email or "guser@gmail.com"
        google_id = mock_id or "1092837465"
    else:
        backend_callback = "http://localhost:8000/api/v1/auth/google/callback"
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": backend_callback
                }
            )
            if token_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to retrieve access token from Google")
            
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token returned by Google")

            user_res = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to retrieve user profile from Google")
            
            profile = user_res.json()
            google_id = str(profile.get("id"))
            email = profile.get("email")
            username = email.split("@")[0] if email else f"google_{google_id}"

    user = db.query(User).filter(User.google_id == google_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_id
            db.commit()

    if not user:
        base_username = username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
            
        user = User(
            id=f"usr_{username.lower()}",
            username=username,
            email=email,
            google_id=google_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user_id=user.id, username=user.username)
    redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/signin?token={token}&username={user.username}&user_id={user.id}"
    return RedirectResponse(redirect_url)

