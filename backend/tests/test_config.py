import pytest
from pydantic import ValidationError

from backend.app.config import Settings, settings


def test_runtime_settings_loaded_for_tests():
    assert settings.PORT == 8000
    assert settings.HOST == "0.0.0.0"
    assert settings.DEBUG is True
    assert "sqlite" in settings.DATABASE_URL
    assert settings.SECRET_KEY


def test_storage_config_validation():
    with pytest.raises(ValueError, match="Cloud storage configuration is missing"):
        Settings(
            DEBUG=False,
            SECRET_KEY="supersecretkeythatisatleast32charslong",
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            FIRE_CROW_SCANNER_IMAGE="image:1.0",
            REPORT_LOCAL_FALLBACK=False,
            R2_ACCESS_KEY_ID="",
        )

    Settings(
        DEBUG=False,
        SECRET_KEY="supersecretkeythatisatleast32charslong",
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        FIRE_CROW_SCANNER_IMAGE="image:1.0",
        REPORT_LOCAL_FALLBACK=True,
    )


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


def test_settings_do_not_hardcode_local_frontend_url():
    configured = Settings(
        _env_file=None,  # type: ignore
        DEBUG=False,
        SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
    )

    assert configured.FRONTEND_URL == ""


def test_settings_accepts_comma_separated_github_oauth_scopes_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_OAUTH_SCOPES", "repo, workflow, read:org, user:email")

    configured = Settings(
        DEBUG=False,
        SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
    )

    assert configured.GITHUB_OAUTH_SCOPES == ["repo", "workflow", "read:org", "user:email"]


def test_settings_accepts_json_github_oauth_scopes_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_OAUTH_SCOPES", '["repo","workflow","read:org","user:email"]')

    configured = Settings(
        DEBUG=False,
        SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
    )

    assert configured.GITHUB_OAUTH_SCOPES == ["repo", "workflow", "read:org", "user:email"]


def test_safe_llm_flags_default_disabled():
    configured = Settings(
        DEBUG=False,
        SECRET_KEY="x" * 40,
        DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
    )

    assert configured.LLM_CHAT_ASSISTANT is False
    assert configured.LLM_DASHBOARD_INSIGHT is False
    assert configured.LLM_ATTACK_CHAIN_NAMING is False
    assert configured.LLM_PR_DESCRIPTION is False
