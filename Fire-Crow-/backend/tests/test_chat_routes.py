from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_auth import PRIVACY_POLICY_VERSION
from app.models import AuditJob, FindingModel, SessionLocal
from app.schemas import JobStatus, Severity

client = TestClient(app)


def _auth_session(username: str = "chat-auditor") -> tuple[dict[str, str], str]:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "supersecretpassword",
            "privacy_policy_accepted": True,
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )
    user_id = register_response.json()["user_id"]
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "supersecretpassword",
            "privacy_policy_accepted": True,
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
        },
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


def test_chat_route_returns_503_when_disabled(monkeypatch):
    headers, user_id = _auth_session()
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-chat-disabled",
                user_id=user_id,
                repo_url="https://example.com/repo",
                repo_branch="main",
                status=JobStatus.COMPLETED,
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("app.api.routes_chat.is_llm_enabled", lambda feature: False)

    response = client.post(
        "/api/v1/chat/ask",
        json={"job_id": "job-chat-disabled", "message": "Summarize the findings"},
        headers=headers,
    )

    assert response.status_code == 503
    assert "disabled" in response.json()["detail"].lower()


def test_chat_route_returns_safe_llm_response(monkeypatch):
    headers, user_id = _auth_session("chat-enabled-auditor")
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-chat-enabled",
                user_id=user_id,
                repo_url="https://example.com/repo",
                repo_branch="main",
                status=JobStatus.COMPLETED,
            )
        )
        db.add(
            FindingModel(
                id="finding-chat-1",
                job_id="job-chat-enabled",
                agent_source="SAST",
                title="SQL Injection",
                description="Unsanitized query builder",
                severity=Severity.HIGH,
                evidence="SELECT * FROM users WHERE id = " + "{input}",
            )
        )
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("app.api.routes_chat.is_llm_enabled", lambda feature: True)
    monkeypatch.setattr("app.api.routes_chat.safe_llm_call", lambda *args, **kwargs: "Focus on the SQL injection finding first.")

    response = client.post(
        "/api/v1/chat/ask",
        json={"job_id": "job-chat-enabled", "message": "What should I fix first?"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Focus on the SQL injection finding first."
