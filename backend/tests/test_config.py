import os
from backend.app.config import settings


def test_settings_default_values():
    # Verify defaults are set correctly
    assert settings.PORT == 8000
    assert settings.HOST == "0.0.0.0"
    assert settings.DEBUG is True
    assert "postgresql" in settings.DATABASE_URL or "sqlite" in settings.DATABASE_URL
    assert "redis" in settings.REDIS_URL
