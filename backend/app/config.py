import os
import json
from pathlib import Path
from typing import Annotated, Any
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode
from pydantic import Field, field_validator, model_validator


BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # --- Server Settings ---
    PORT: int = Field(default=8000, validation_alias="PORT")
    HOST: str = Field(default="0.0.0.0", validation_alias="HOST")
    DEBUG: bool = Field(default=False, validation_alias="DEBUG")
    SECRET_KEY: str = Field(default="", validation_alias="SECRET_KEY")
    ENCRYPTION_KEY: str = Field(default="", validation_alias="ENCRYPTION_KEY")
    FRONTEND_URL: str = Field(default="", validation_alias="FRONTEND_URL")
    CORS_ORIGINS: str = Field(default="", validation_alias="CORS_ORIGINS")

    # --- Security and Compliance Constants ---
    PRIVACY_POLICY_VERSION: str = Field(default="2026-06-06", validation_alias="PRIVACY_POLICY_VERSION")
    TERMS_VERSION: str = Field(default="2026-06-06", validation_alias="TERMS_VERSION")
    GITHUB_OAUTH_SCOPES: Annotated[list[str], NoDecode] = Field(
        default=["repo", "workflow", "read:org", "user:email"],
        validation_alias="GITHUB_OAUTH_SCOPES"
    )
    LOGIN_FAILURE_WINDOW_MINUTES: int = Field(default=10, validation_alias="LOGIN_FAILURE_WINDOW_MINUTES")
    LOGIN_FAILURE_LIMIT: int = Field(default=5, validation_alias="LOGIN_FAILURE_LIMIT")
    MAX_REQUEST_BODY_BYTES: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_REQUEST_BODY_BYTES")  # 10MB
    MAX_JSON_BODY_BYTES: int = Field(default=2 * 1024 * 1024, validation_alias="MAX_JSON_BODY_BYTES")  # 2MB
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24, validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    AUTH_COOKIE_NAME: str = Field(default="fc_access_token", validation_alias="AUTH_COOKIE_NAME")
    AUTH_COOKIE_SECURE: bool = Field(default=True, validation_alias="AUTH_COOKIE_SECURE")
    AUTH_COOKIE_HTTPONLY: bool = Field(default=True, validation_alias="AUTH_COOKIE_HTTPONLY")
    AUTH_COOKIE_SAMESITE: str = Field(default="lax", validation_alias="AUTH_COOKIE_SAMESITE")


    # --- Database & Cache ---
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/firecrow",
        validation_alias="DATABASE_URL"
    )
    REDIS_URL: str = Field(
        default="",
        validation_alias="REDIS_URL"
    )
    REDIS_PASSWORD: str = Field(default="", validation_alias="REDIS_PASSWORD")
    FIRE_CROW_MOCK_SANDBOX: bool = Field(default=False, validation_alias="FIRE_CROW_MOCK_SANDBOX")
    FIRE_CROW_ALLOW_UNTRUSTED_DOCKERFILE_BUILD: bool = Field(
        default=False,
        validation_alias="FIRE_CROW_ALLOW_UNTRUSTED_DOCKERFILE_BUILD",
    )
    FIRE_CROW_SCANNER_IMAGE: str = Field(
        default="ghcr.io/johan-droid/firecrow-scanner:2026-06-06",
        validation_alias="FIRE_CROW_SCANNER_IMAGE",
    )

    # --- GitHub Integrations ---
    GITHUB_CLIENT_ID: str = Field(default="", validation_alias="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: str = Field(default="", validation_alias="GITHUB_CLIENT_SECRET")
    GITHUB_TOKEN: str = Field(default="", validation_alias="GITHUB_TOKEN")

    # --- Google Integrations ---
    GOOGLE_CLIENT_ID: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")

    # --- Communication ---
    RESEND_API_KEY: str = Field(default="", validation_alias="RESEND_API_KEY")
    BREVO_API_KEY: str = Field(default="", validation_alias="BREVO_API_KEY")
    SENDER_EMAIL: str = Field(default="reports@firecrow.dev", validation_alias="SENDER_EMAIL")

    # --- Google/SMTP Mail ---
    SMTP_HOST: str = Field(default="smtp.gmail.com", validation_alias="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, validation_alias="SMTP_PORT")
    SMTP_USER: str = Field(default="", validation_alias="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="", validation_alias="SMTP_PASSWORD")

    # --- Report Storage (Cloudflare R2) ---
    R2_ACCESS_KEY_ID: str = Field(default="", validation_alias="R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY: str = Field(default="", validation_alias="R2_SECRET_ACCESS_KEY")
    R2_ENDPOINT_URL: str = Field(default="", validation_alias="R2_ENDPOINT_URL")
    R2_BUCKET_NAME: str = Field(default="firecrow-reports", validation_alias="R2_BUCKET_NAME")

    # --- AI Models API Keys ---
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash", validation_alias="GEMINI_MODEL")

    # --- Gemini Tuning ---
    GEMINI_FALLBACK_MODEL: str = Field(default="gemini-1.5-pro", validation_alias="GEMINI_FALLBACK_MODEL")
    GEMINI_ENABLE_FALLBACK_MODEL: bool = Field(default=True, validation_alias="GEMINI_ENABLE_FALLBACK_MODEL")
    GEMINI_MAX_ATTEMPTS: int = Field(default=3, validation_alias="GEMINI_MAX_ATTEMPTS")
    GEMINI_TIMEOUT_SECONDS: int = Field(default=30, validation_alias="GEMINI_TIMEOUT_SECONDS")
    GEMINI_MAX_FINDINGS_PER_CALL: int = Field(default=50, validation_alias="GEMINI_MAX_FINDINGS_PER_CALL")
    GEMINI_MAX_PROMPT_CHARS: int = Field(default=100000, validation_alias="GEMINI_MAX_PROMPT_CHARS")
    GEMINI_DAILY_SOFT_LIMIT: int = Field(default=1000, validation_alias="GEMINI_DAILY_SOFT_LIMIT")
    GEMINI_MIN_SECONDS_BETWEEN_CALLS: int = Field(default=1, validation_alias="GEMINI_MIN_SECONDS_BETWEEN_CALLS")

    # --- Orchestration Tunables ---
    MAX_ACTIVE_JOBS_PER_USER: int = Field(default=5, validation_alias="MAX_ACTIVE_JOBS_PER_USER")
    BROKER_CONNECTION_TIMEOUT: float = Field(default=0.5, validation_alias="BROKER_CONNECTION_TIMEOUT")
    SSE_POLL_INTERVAL: float = Field(default=0.5, validation_alias="SSE_POLL_INTERVAL")
    SSE_HEARTBEAT_INTERVAL: float = Field(default=15.0, validation_alias="SSE_HEARTBEAT_INTERVAL")
    REPORT_PRESIGNED_TTL: int = Field(default=3600, validation_alias="REPORT_PRESIGNED_TTL")
    REPORT_LOCAL_FALLBACK: bool = Field(default=True, validation_alias="REPORT_LOCAL_FALLBACK")
    MAX_SCAN_DURATION: int = Field(default=2700, validation_alias="MAX_SCAN_DURATION")
    DEFAULT_BUDGET_USD: float = Field(default=5.0, validation_alias="DEFAULT_BUDGET_USD")
    SCANNER_COMMAND_TIMEOUT: int = Field(default=600, validation_alias="SCANNER_COMMAND_TIMEOUT")
    SCANNER_OUTPUT_MAX_LENGTH: int = Field(default=50000, validation_alias="SCANNER_OUTPUT_MAX_LENGTH")
    API_DISCOVERY_LIMIT: int = Field(default=50, validation_alias="API_DISCOVERY_LIMIT")
    GEMINI_FINDINGS_CHUNK_SIZE: int = Field(default=50, validation_alias="GEMINI_FINDINGS_CHUNK_SIZE")

    # --- Scoring Tunables ---
    SCORING_CRITICAL: float = Field(default=9.8, validation_alias="SCORING_CRITICAL")
    SCORING_HIGH: float = Field(default=8.5, validation_alias="SCORING_HIGH")
    SCORING_MEDIUM: float = Field(default=5.5, validation_alias="SCORING_MEDIUM")
    SCORING_LOW: float = Field(default=2.5, validation_alias="SCORING_LOW")
    SCORING_INFO: float = Field(default=0.0, validation_alias="SCORING_INFO")

    # --- Sandbox launch profiles config ---
    SANDBOX_PYTHON_IMAGE: str = Field(default="python:3.12-alpine", validation_alias="SANDBOX_PYTHON_IMAGE")
    SANDBOX_NODE_IMAGE: str = Field(default="node:20-alpine", validation_alias="SANDBOX_NODE_IMAGE")

    # --- Reporter Tuning ---
    REPORT_COMPACT_MODE: bool = Field(default=False, validation_alias="REPORT_COMPACT_MODE")
    REPORT_MAX_PAGES: int = Field(default=50, validation_alias="REPORT_MAX_PAGES")
    REPORT_MAX_FINDINGS_IN_PDF: int = Field(default=100, validation_alias="REPORT_MAX_FINDINGS_IN_PDF")
    REPORT_MAX_EVIDENCE_CHARS: int = Field(default=2000, validation_alias="REPORT_MAX_EVIDENCE_CHARS")
    REPORT_MAX_REMEDIATION_CHARS: int = Field(default=2000, validation_alias="REPORT_MAX_REMEDIATION_CHARS")
    REPORT_INCLUDE_DETAILED_FINDINGS: bool = Field(default=True, validation_alias="REPORT_INCLUDE_DETAILED_FINDINGS")
    REPORT_STORE_FULL_ARTIFACT_JSON: bool = Field(default=True, validation_alias="REPORT_STORE_FULL_ARTIFACT_JSON")
    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")

    model_config = SettingsConfigDict(
        env_file=(
            WORKSPACE_DIR / ".env",
            BACKEND_DIR / ".env",
            WORKSPACE_DIR / ".env.local",
            BACKEND_DIR / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("GITHUB_OAUTH_SCOPES", mode="before")
    @classmethod
    def parse_github_oauth_scopes(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        if value is None:
            return ["repo", "workflow", "read:org", "user:email"]

        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ["repo", "workflow", "read:org", "user:email"]

            if raw.startswith("["):
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("GITHUB_OAUTH_SCOPES JSON value must be a list.")
                return [str(item).strip() for item in parsed if str(item).strip()]

            return [scope.strip() for scope in raw.split(",") if scope.strip()]

        raise ValueError("Unsupported GITHUB_OAUTH_SCOPES value.")

    @model_validator(mode="after")
    def validate_production_keys(self) -> "Settings":
        insecure_dev_values = {
            "",
            "dev_secret_key_change_in_production_1234567890",
            "change_me",
            "changeme",
            "secret",
            "development",
        }

        if self.DEBUG and not self.SECRET_KEY:
            object.__setattr__(
                self,
                "SECRET_KEY",
                "dev_only_firecrow_local_secret_key_32_bytes_minimum",
            )

        if not self.DEBUG:
            if self.SECRET_KEY.strip() in insecure_dev_values:
                raise ValueError("SECRET_KEY is required in production and cannot use a known development value.")
            if len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production.")
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("SQLite DATABASE_URL is only allowed when DEBUG=True.")
            if self.FIRE_CROW_SCANNER_IMAGE.endswith(":latest"):
                raise ValueError("FIRE_CROW_SCANNER_IMAGE must be pinned in production and cannot use :latest.")
            if not getattr(self, "REPORT_LOCAL_FALLBACK", True):
                if not self.R2_ACCESS_KEY_ID or not self.R2_SECRET_ACCESS_KEY or not self.R2_BUCKET_NAME or not self.R2_ENDPOINT_URL:
                    raise ValueError("Cloud storage configuration is missing, but REPORT_LOCAL_FALLBACK is False.")

        # Inject REDIS_PASSWORD into REDIS_URL if provided
        if self.REDIS_PASSWORD:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(self.REDIS_URL)
            if parsed.scheme in ("redis", "rediss") and not parsed.password:
                netloc = parsed.netloc
                if "@" in netloc:
                    user_host = netloc.split("@", 1)
                    user = user_host[0]
                    host = user_host[1]
                    if ":" not in user:
                        netloc = f"{user}:{self.REDIS_PASSWORD}@{host}"
                else:
                    netloc = f":{self.REDIS_PASSWORD}@{netloc}"
                new_url = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
                object.__setattr__(self, "REDIS_URL", new_url)
        return self


# Global settings instance
settings = Settings()

_global_state = {
    "r2_disabled": False
}

