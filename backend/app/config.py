from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # --- Server Settings ---
    PORT: int = Field(default=8000, validation_alias="PORT")
    HOST: str = Field(default="0.0.0.0", validation_alias="HOST")
    DEBUG: bool = Field(default=True, validation_alias="DEBUG")
    SECRET_KEY: str = Field(default="dev_secret_key_change_in_production_1234567890", validation_alias="SECRET_KEY")
    FRONTEND_URL: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_URL")

    # --- Database & Cache ---
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/firecrow",
        validation_alias="DATABASE_URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL"
    )
    REDIS_PASSWORD: str = Field(default="", validation_alias="REDIS_PASSWORD")
    FIRE_CROW_MOCK_SANDBOX: bool = Field(default=True, validation_alias="FIRE_CROW_MOCK_SANDBOX")

    # --- GitHub Integrations ---
    GITHUB_CLIENT_ID: str = Field(default="", validation_alias="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: str = Field(default="", validation_alias="GITHUB_CLIENT_SECRET")
    GITHUB_TOKEN: str = Field(default="", validation_alias="GITHUB_TOKEN")

    # --- Google Integrations ---
    GOOGLE_CLIENT_ID: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")

    # --- Communication ---
    RESEND_API_KEY: str = Field(default="", validation_alias="RESEND_API_KEY")
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

    @model_validator(mode="after")
    def validate_production_keys(self) -> "Settings":
        # Check defaults in production context if not debug
        if not self.DEBUG:
            if self.SECRET_KEY == "dev_secret_key_change_in_production_1234567890":
                raise ValueError("Insecure default SECRET_KEY cannot be used in production.")
        return self


# Global settings instance
settings = Settings()
