from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.auth import create_access_token, verify_access_token

client = TestClient(app)


def test_jwt_generation_and_verification():
    user_id = "usr_tester"
    token = create_access_token(user_id=user_id, username="tester")
    
    assert token is not None
    assert isinstance(token, str)
    
    payload = verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["username"] == "tester"


def test_auth_me_unauthorized():
    # Calling secured route without Authorization header
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_auth_me_authorized():
    # Login and call me endpoint
    login_response = client.post("/api/v1/auth/login", json={"username": "supertester"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == "usr_supertester"
    assert response.json()["role"] == "security_engineer"


def test_registration_and_login_flow():
    # 1. Register a new user
    reg_response = client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "password": "supersecretpassword", "email": "newuser@example.com"}
    )
    assert reg_response.status_code == 200
    token = reg_response.json()["access_token"]
    assert reg_response.json()["username"] == "newuser"

    # 2. Login with correct password
    login_ok = client.post(
        "/api/v1/auth/login",
        json={"username": "newuser", "password": "supersecretpassword"}
    )
    assert login_ok.status_code == 200
    assert login_ok.json()["access_token"] is not None

    # 3. Login with incorrect password
    login_fail = client.post(
        "/api/v1/auth/login",
        json={"username": "newuser", "password": "wrongpassword"}
    )
    assert login_fail.status_code == 401
    assert "Invalid" in login_fail.json()["detail"]


def test_github_oauth_mock_redirect():
    response = client.get("/api/v1/auth/github")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Fire Crow - Mock GitHub OAuth" in response.text


def test_github_oauth_mock_callback():
    response = client.get(
        "/api/v1/auth/github/callback",
        params={
            "code": "mock_github_code",
            "mock_username": "oauth_octocat",
            "mock_email": "octocat@github.dev",
            "mock_id": "999888"
        },
        follow_redirects=False
    )
    assert response.status_code == 307
    location = response.headers["location"]
    assert "/signin" in location
    assert "token=" in location
    assert "username=oauth_octocat" in location
    assert "user_id=usr_oauth_octocat" in location


def test_google_oauth_mock_redirect():
    response = client.get("/api/v1/auth/google")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Fire Crow - Mock Google OAuth" in response.text


def test_google_oauth_mock_callback():
    response = client.get(
        "/api/v1/auth/google/callback",
        params={
            "code": "mock_google_code",
            "mock_username": "oauth_guser",
            "mock_email": "guser@gmail.dev",
            "mock_id": "777666"
        },
        follow_redirects=False
    )
    assert response.status_code == 307
    location = response.headers["location"]
    assert "/signin" in location
    assert "token=" in location
    assert "username=oauth_guser" in location
    assert "user_id=usr_oauth_guser" in location

