import pytest
from pydantic import ValidationError

from app.config import Settings, WORKSPACE_DIR, settings

# Minimal production-valid defaults that all DEBUG=False test cases need.
# Individual tests can override any of these to trigger validation errors.
_PROD_DEFAULTS = dict(
    DEBUG=False,
    SECRET_KEY="x" * 40,
    ENCRYPTION_KEY="y" * 40,
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
    REDIS_URL="redis://localhost:6379/0",
    FRONTEND_URL="https://app.firecrow.test",
    CORS_ORIGINS="https://app.firecrow.test",
)


def _prod_settings(**overrides) -> Settings:
    """Create a Settings instance with production-safe defaults, allowing overrides."""
    return Settings(**{**_PROD_DEFAULTS, **overrides})


def test_runtime_settings_loaded_for_tests():
    assert settings.PORT == 8000
    assert settings.HOST == "0.0.0.0"
    assert settings.DEBUG is True
    assert "sqlite" in settings.DATABASE_URL
    assert settings.SECRET_KEY


def test_storage_config_validation():
    with pytest.raises(ValueError, match="Cloud storage configuration is missing"):
        _prod_settings(
            FIRE_CROW_SCANNER_IMAGE="image:1.0",
            REPORT_LOCAL_FALLBACK=False,
            R2_ACCESS_KEY_ID="",
        )

    _prod_settings(
        FIRE_CROW_SCANNER_IMAGE="image:1.0",
        REPORT_LOCAL_FALLBACK=True,
    )


def test_settings_debug_defaults_safe_when_secret_provided():
    configured = _prod_settings()
    assert configured.DEBUG is False


def test_settings_rejects_missing_secret_in_production():
    with pytest.raises(ValidationError):
        _prod_settings(SECRET_KEY="", ENCRYPTION_KEY="y" * 40)


def test_settings_rejects_default_secret_in_production():
    with pytest.raises(ValidationError):
        _prod_settings(
            SECRET_KEY="dev_only_firecrow_local_secret_key_32_bytes_minimum_DO_NOT_USE_IN_PRODUCTION",
            ENCRYPTION_KEY="y" * 40,
        )


def test_settings_rejects_sqlite_in_production():
    with pytest.raises(ValidationError):
        _prod_settings(DATABASE_URL="sqlite:///firecrow.db")


def test_settings_normalize_relative_sqlite_database_url():
    configured = Settings(
        _env_file=None,  # type: ignore
        DEBUG=True,
        SECRET_KEY="x" * 40,
        ENCRYPTION_KEY="y" * 40,
        DATABASE_URL="sqlite:///./firecrow.db",
    )

    expected = f"sqlite:///{(WORKSPACE_DIR / 'firecrow.db').resolve().as_posix()}"
    assert configured.DATABASE_URL == expected


def test_settings_rejects_latest_scanner_image_in_production():
    with pytest.raises(ValidationError):
        _prod_settings(FIRE_CROW_SCANNER_IMAGE="kalilinux/kali-rolling:latest")


def test_settings_do_not_hardcode_local_frontend_url():
    configured = Settings(
        _env_file=None,  # type: ignore
        DEBUG=True,
        SECRET_KEY="x" * 40,
        ENCRYPTION_KEY="y" * 40,
        DATABASE_URL="postgresql://postgres:postgres@localhost:5432/firecrow",
        FRONTEND_URL="",
    )
    # In debug mode FRONTEND_URL can be empty
    assert configured.FRONTEND_URL == ""


def test_settings_accepts_comma_separated_github_oauth_scopes_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_OAUTH_SCOPES", "repo, workflow, read:org, user:email")

    configured = _prod_settings()
    assert configured.GITHUB_OAUTH_SCOPES == ["repo", "workflow", "read:org", "user:email"]


def test_settings_accepts_json_github_oauth_scopes_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_OAUTH_SCOPES", '["repo","workflow","read:org","user:email"]')

    configured = _prod_settings()
    assert configured.GITHUB_OAUTH_SCOPES == ["repo", "workflow", "read:org", "user:email"]


def test_safe_llm_flags_default_disabled():
    configured = _prod_settings()
    assert configured.LLM_CHAT_ASSISTANT is False
    assert configured.LLM_DASHBOARD_INSIGHT is False
    assert configured.LLM_ATTACK_CHAIN_NAMING is False
    assert configured.LLM_PR_DESCRIPTION is False


def test_settings_allows_encryption_key_to_fall_back_to_secret_key_in_production():
    configured = _prod_settings(ENCRYPTION_KEY="")
    assert configured.ENCRYPTION_KEY == configured.SECRET_KEY


def test_settings_rejects_short_encryption_key_in_production():
    with pytest.raises(ValidationError):
        _prod_settings(ENCRYPTION_KEY="too_short")


def test_settings_rejects_default_encryption_key_in_production():
    with pytest.raises(ValidationError):
        _prod_settings(ENCRYPTION_KEY="local_dev_encryption_key_change_me_1234567890")


def test_settings_allows_missing_cors_origins_and_frontend_url_in_production():
    configured = _prod_settings(CORS_ORIGINS="", FRONTEND_URL="", REDIS_URL="")
    assert configured.CORS_ORIGINS == ""
    assert configured.FRONTEND_URL == ""
    assert configured.REDIS_URL == ""


def test_settings_allow_optional_oauth_integrations_in_production():
    configured = _prod_settings(
        GITHUB_CLIENT_ID="",
        GITHUB_CLIENT_SECRET="",
    )
    assert configured.GITHUB_CLIENT_ID == ""


def test_settings_default_postgres_migration_source_url_tracks_database_url():
    configured = _prod_settings()
    assert configured.POSTGRES_MIGRATION_SOURCE_URL == configured.DATABASE_URL


def test_settings_require_neo4j_fields_when_graph_backend_selected():
    with pytest.raises(ValidationError):
        _prod_settings(
            DATABASE_BACKEND="neo4j",
            DATABASE_URL="",
            NEO4J_URI="",
            NEO4J_USER="",
            NEO4J_PASSWORD="",
        )


def test_settings_accept_local_neo4j_backend_with_secure_password():
    configured = _prod_settings(
        DATABASE_BACKEND="neo4j",
        DATABASE_URL="",
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USER="neo4j",
        NEO4J_PASSWORD="a_secure_neo4j_password",
    )
    assert configured.DATABASE_BACKEND == "neo4j"
    assert configured.NEO4J_URI == "bolt://localhost:7687"


def test_settings_reject_remote_neo4j_without_tls():
    with pytest.raises(ValidationError):
        _prod_settings(
            DATABASE_BACKEND="neo4j",
            DATABASE_URL="",
            NEO4J_URI="bolt://graph.firecrow.test:7687",
            NEO4J_USER="neo4j",
            NEO4J_PASSWORD="a_secure_neo4j_password",
        )
