import pytest
from backend.app.agents.ai_analyzer import ai_analyzer_body
from backend.app.schemas.audit_state import AuditState, Finding, Severity
from unittest.mock import patch, MagicMock

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
