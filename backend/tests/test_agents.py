import pytest
from backend.app.agents.ai_analyzer import ai_analyzer_body
from backend.app.schemas.audit_state import AuditState, Finding, Severity
from unittest.mock import patch, MagicMock
import json

def test_gemini_fallback_no_model():
    state = AuditState(job_id="test_job")
    db_mock = MagicMock()
    
    with patch('backend.app.config.settings') as mock_settings:
        mock_settings.GEMINI_MODEL = ""
        mock_settings.DEBUG = True

        result = ai_analyzer_body(db_mock, state)

        # Verify it went to deterministic fallback
        assert "fallback_report" in result
        assert "deduplicated_findings" in result
        assert "email_body" in result
        assert "pr_body" in result

def test_gemini_fallback_api_error():
    state = AuditState(job_id="test_job")
    db_mock = MagicMock()
    
    with patch('backend.app.agents.ai_analyzer.run_ai_analyzer') as mock_ai:
        mock_ai.side_effect = Exception("API Timeout")

        with patch('backend.app.config.settings') as mock_settings:
            mock_settings.GEMINI_MODEL = "gemini-1.5-pro"

            result = ai_analyzer_body(db_mock, state)

            # Verify exception routes to fallback
            assert "fallback_report" in result


def test_google_agent_retry_on_429():
    from backend.app.agents.google_agent import run_google_agent
    from backend.app.schemas.audit_state import Finding, Severity
    
    findings = [Finding(id="f1", title="SQL Injection", description="Test vulnerability", severity=Severity.HIGH, agent_source="SAST")]
    remediations = []
    
    with patch("urllib.request.urlopen") as mock_urlopen, \
         patch("backend.app.agents.google_agent.settings") as mock_settings:
         
        mock_settings.GEMINI_API_KEY = "test_key"
        mock_settings.GEMINI_MODEL = "gemini-1.5-pro"
        mock_settings.GEMINI_ENABLE_FALLBACK_MODEL = True
        mock_settings.GEMINI_FALLBACK_MODEL = "gemini-1.5-flash"
        mock_settings.DEBUG = False
        
        # Mock SMTP to prevent actual email sending
        with patch("smtplib.SMTP") as mock_smtp:
            # First call returns 429 HTTPError, second succeeds
            from urllib.error import HTTPError
            import io
            
            from email.message import Message
            http_err = HTTPError("url", 429, "Too Many Requests", Message(), io.BytesIO(b""))
            
            success_response = MagicMock()
            success_response.__enter__.return_value = success_response
            success_response.read.return_value = json.dumps({
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": json.dumps({
                                "overall_pr_risk": "HIGH",
                                "risk_description": "Mocked analysis description",
                                "key_risk_factors": ["Vulnerability detected"],
                                "merge_recommendation": "REVIEW"
                            })
                        }]
                    }
                }]
            }).encode("utf-8")
            
            mock_urlopen.side_effect = [http_err, success_response]
            
            result = run_google_agent(
                job_id="test_job",
                repo_url="https://github.com/example/repo",
                findings=findings,
                remediations=remediations,
                recipient_email="test@example.com"
            )
            
            assert result["google_agent_pr_risks_analyzed"] is True
            assert result["google_agent_risk_report"]["overall_pr_risk"] == "HIGH"
            assert mock_urlopen.call_count == 2


def test_google_agent_all_models_fail():
    from backend.app.agents.google_agent import run_google_agent
    from backend.app.schemas.audit_state import Finding, Severity
    
    findings = [Finding(id="f1", title="SQL Injection", description="Test vulnerability", severity=Severity.HIGH, agent_source="SAST")]
    remediations = []
    
    with patch("urllib.request.urlopen") as mock_urlopen, \
         patch("backend.app.agents.google_agent.settings") as mock_settings:
         
        mock_settings.GEMINI_API_KEY = "test_key"
        mock_settings.GEMINI_MODEL = "gemini-1.5-pro"
        mock_settings.GEMINI_ENABLE_FALLBACK_MODEL = True
        mock_settings.GEMINI_FALLBACK_MODEL = "gemini-1.5-flash"
        mock_settings.DEBUG = False
        
        from urllib.error import HTTPError
        import io
        
        from email.message import Message
        http_err_429 = HTTPError("url", 429, "Too Many Requests", Message(), io.BytesIO(b""))
        http_err_500 = HTTPError("url", 500, "Internal Error", Message(), io.BytesIO(b""))
        
        mock_urlopen.side_effect = [http_err_429, http_err_500]
        
        result = run_google_agent(
            job_id="test_job",
            repo_url="https://github.com/example/repo",
            findings=findings,
            remediations=remediations,
            recipient_email="test@example.com"
        )
        
        assert result["google_agent_pr_risks_analyzed"] is False
        assert result["google_agent_delivered"] is False
        assert mock_urlopen.call_count == 2

