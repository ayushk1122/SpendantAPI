from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, ValidationError, field_validator
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
    plaid_client_id: str = Field(..., alias="PLAID_CLIENT_ID")
    plaid_secret: str = Field(..., alias="PLAID_SECRET")
    plaid_env: Literal["sandbox", "development", "production"] = Field(..., alias="PLAID_ENV")
    plaid_storage_path: str = Field(default="data/plaid.sqlite3", alias="PLAID_STORAGE_PATH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

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
