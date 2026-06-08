import pytest
from backend.app.orchestrator.maestro import ai_analyzer_body
from backend.app.schemas.audit_state import AuditState
from unittest.mock import patch, MagicMock

def test_maestro_ai_analyzer_routing():
    state = AuditState(job_id="test_job")
    db_mock = MagicMock()
    
    with patch('backend.app.config.settings') as mock_settings:
        mock_settings.GEMINI_MODEL = ""

        result = ai_analyzer_body(db_mock, state)
        assert "fallback_report" in result
