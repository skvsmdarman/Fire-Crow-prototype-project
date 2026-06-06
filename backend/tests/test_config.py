import pytest
from pydantic import ValidationError

from backend.app.config import Settings, settings


def test_runtime_settings_loaded_for_tests():
    assert settings.PORT == 8000
    assert settings.HOST == "0.0.0.0"
    assert settings.DEBUG is True
    assert "sqlite" in settings.DATABASE_URL
    assert settings.SECRET_KEY


def test_settings_debug_defaults_safe_when_secret_provided():
    configured = Settings(
        DEBUG=False,
        SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
    )

    assert configured.DEBUG is False


def test_settings_rejects_missing_secret_in_production():
    with pytest.raises(ValidationError):
        Settings(
            DEBUG=False,
            SECRET_KEY="",
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
        )


def test_settings_rejects_default_secret_in_production():
    with pytest.raises(ValidationError):
        Settings(
            DEBUG=False,
            SECRET_KEY="dev_secret_key_change_in_production_1234567890",
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
        )


def test_settings_rejects_sqlite_in_production():
    with pytest.raises(ValidationError):
        Settings(DEBUG=False, SECRET_KEY="x" * 40, DATABASE_URL="sqlite:///firecrow.db")


def test_settings_rejects_latest_scanner_image_in_production():
    with pytest.raises(ValidationError):
        Settings(
            DEBUG=False,
            SECRET_KEY="x" * 40,
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
            FIRE_CROW_SCANNER_IMAGE="kalilinux/kali-rolling:latest",
        )
