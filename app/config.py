from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    app_env: Literal["local", "staging", "production"] = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_client_user_id: str = Field(
        default="spendant-local-user",
        alias="DEFAULT_CLIENT_USER_ID",
    )
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")
    api_public_base_url: str | None = Field(default=None, alias="API_PUBLIC_BASE_URL")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    token_encryption_key: str = Field(
        default="local-dev-token-encryption-key",
        alias="TOKEN_ENCRYPTION_KEY",
    )
    token_key_version: str = Field(default="v1", alias="TOKEN_KEY_VERSION")
    auth_required: bool | None = Field(default=None, alias="AUTH_REQUIRED")
    auth_issuer: str | None = Field(default=None, alias="AUTH_ISSUER")
    auth_audience: str | None = Field(default=None, alias="AUTH_AUDIENCE")
    auth_jwks_url: str | None = Field(default=None, alias="AUTH_JWKS_URL")
    auth_user_id_claim: str = Field(default="sub", alias="AUTH_USER_ID_CLAIM")
    plaid_client_id: str = Field(..., alias="PLAID_CLIENT_ID")
    plaid_secret: str = Field(..., alias="PLAID_SECRET")
    plaid_env: Literal["sandbox", "development", "production"] = Field(..., alias="PLAID_ENV")
    plaid_storage_path: str = Field(default="data/plaid.sqlite3", alias="PLAID_STORAGE_PATH")
    plaid_webhook_verification_key: str | None = Field(
        default=None,
        alias="PLAID_WEBHOOK_VERIFICATION_KEY",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.auth_required is None:
            self.auth_required = self.app_env != "local"

        if self.auth_required:
            missing = [
                name
                for name, value in {
                    "AUTH_ISSUER": self.auth_issuer,
                    "AUTH_AUDIENCE": self.auth_audience,
                    "AUTH_JWKS_URL": self.auth_jwks_url,
                }.items()
                if not value
            ]
            if missing:
                raise ValueError(
                    "Missing required auth settings when AUTH_REQUIRED is enabled: "
                    + ", ".join(missing)
                )

        if self.app_env == "production" and not self.api_public_base_url:
            raise ValueError("API_PUBLIC_BASE_URL is required when APP_ENV=production.")

        return self

    @property
    def allows_local_identity_bypass(self) -> bool:
        return self.app_env == "local" and not self.auth_required

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins.strip():
            return []

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


class ConfigurationError(RuntimeError):
    pass


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing_fields = [
            ".".join(str(part) for part in error["loc"])
            for error in exc.errors()
            if error["type"] == "missing"
        ]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ConfigurationError(f"Missing required environment variables: {missing}") from exc
        raise ConfigurationError(f"Invalid environment configuration: {exc}") from exc
