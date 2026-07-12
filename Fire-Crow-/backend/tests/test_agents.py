from unittest.mock import MagicMock, patch

from app.agents.ai_analyzer import ai_analyzer_body, run_ai_analyzer
from app.agents.google_agent import run_google_agent
from app.schemas.audit_state import AuditState, Finding, Severity


def test_ai_analyzer_deduplicates_deterministically_without_remediations():
    duplicate_a = Finding(
        id="f-1",
        agent_source="SAST",
        title="SQL Injection",
        description="Short description",
        severity=Severity.HIGH,
        evidence="raw sql query",
        file_path="app/db.py",
        line_number=10,
    )
    duplicate_b = Finding(
        id="f-2",
        agent_source="SEMGREP",
        title="SQL Injection",
        description="Longer description with more context",
        severity=Severity.HIGH,
        evidence="raw sql query\nwith user-controlled input",
        file_path="app/db.py",
        line_number=10,
    )

    deduped, false_positives, attack_chains, remediations = run_ai_analyzer(
        [duplicate_a],
        [],
        [],
        [],
        [duplicate_b],
    )

    assert len(deduped) == 1
    assert deduped[0].description == "Longer description with more context"
    assert "user-controlled input" in (deduped[0].evidence or "")
    assert false_positives == []
    assert attack_chains == []
    assert remediations == []


def test_ai_analyzer_body_returns_deterministic_payload():
    state = AuditState(
        job_id="test_job",
        static_findings=[
            Finding(
                id="f-1",
                agent_source="SAST",
                title="Hardcoded secret",
                description="A secret was committed.",
                severity=Severity.CRITICAL,
                file_path="app/settings.py",
                line_number=5,
            )
        ],
    )

    result = ai_analyzer_body(MagicMock(), state)

    assert "deduplicated_findings" in result
    assert len(result["deduplicated_findings"]) == 1
    assert result["false_positives"] == []
    assert result["remediations"] == []


def test_google_agent_uses_deterministic_risk_assessment_without_llm():
    findings = [
        Finding(
            id="f1",
            title="SQL Injection",
            description="Unsanitized query path",
            severity=Severity.HIGH,
            agent_source="SAST",
        )
    ]

    with patch("urllib.request.urlopen") as mock_urlopen, patch("smtplib.SMTP") as mock_smtp, patch("app.agents.google_agent.settings") as mock_settings:
        mock_settings.SMTP_USER = "security@example.com"
        mock_settings.SMTP_PASSWORD = "topsecret"
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.RESEND_API_KEY = ""
        mock_settings.BREVO_API_KEY = ""
        mock_settings.SENDER_EMAIL = "reports@firecrow.dev"
        mock_settings.DEBUG = False

        result = run_google_agent(
            job_id="test_job",
            repo_url="https://github.com/example/repo",
            findings=findings,
            remediations=[],
            recipient_email="team@example.com",
        )

        assert result["google_agent_pr_risks_analyzed"] is True
        assert result["google_agent_risk_report"]["overall_pr_risk"] == "HIGH"
        assert result["google_agent_risk_report"]["merge_recommendation"] == "BLOCK"
        assert mock_smtp.called
        assert not mock_urlopen.called
