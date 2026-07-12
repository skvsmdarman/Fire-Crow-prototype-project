from fastapi.testclient import TestClient

from app.main import app
from app.api.routes_auth import PRIVACY_POLICY_VERSION
from app.models import AuditJob, FindingModel, PushSubscription, SessionLocal
from app.schemas import JobStatus, Severity

client = TestClient(app)


def _auth_session(username: str = "feature-sync-user") -> tuple[dict[str, str], str]:
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


def test_system_status_exposes_llm_feature_flags():
    headers, _ = _auth_session("llm-feature-viewer")

    response = client.get("/api/v1/system/status", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_features"] == {
        "chat_assistant": False,
        "dashboard_insight": False,
        "attack_chain_naming": False,
        "pr_description": False,
    }


def test_leaderboard_returns_score_contract_with_critical_counts():
    headers, user_id = _auth_session("leaderboard-contract-user")
    db = SessionLocal()
    try:
        db.add(
            AuditJob(
                id="job-leaderboard-contract",
                user_id=user_id,
                repo_url="https://github.com/example/repo",
                repo_branch="main",
                status=JobStatus.COMPLETED,
                security_score=82.0,
            )
        )
        db.add_all(
            [
                FindingModel(
                    id="finding-leaderboard-critical-1",
                    job_id="job-leaderboard-contract",
                    agent_source="SAST",
                    title="Critical secret",
                    description="A committed secret.",
                    severity=Severity.CRITICAL,
                ),
                FindingModel(
                    id="finding-leaderboard-critical-2",
                    job_id="job-leaderboard-contract",
                    agent_source="SAST",
                    title="Critical injection",
                    description="A critical injection path.",
                    severity=Severity.CRITICAL,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/leaderboard", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    entry = next(item for item in payload if item["repo_url"] == "https://github.com/example/repo")
    assert entry["score"] == 82.0
    assert entry["security_score"] == 82.0
    assert entry["critical_count"] == 2
    assert "completed_at" in entry


def test_push_subscribe_returns_subscribed_and_persists(monkeypatch):
    headers, user_id = _auth_session("push-contract-user")
    monkeypatch.setattr("app.api.routes_push.load_or_generate_vapid_keys", lambda: ("private", "public"))

    response = client.post(
        "/api/v1/push/subscribe",
        json={
            "endpoint": "https://push.example.test/subscription",
            "p256dh": "p256dh-key",
            "auth": "auth-key",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "subscribed"}

    db = SessionLocal()
    try:
        subscription = db.query(PushSubscription).filter(PushSubscription.endpoint == "https://push.example.test/subscription").first()
        assert subscription is not None
        assert subscription.user_id == user_id
    finally:
        db.close()
