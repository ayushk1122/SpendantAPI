import pytest
from pydantic import ValidationError

from app.config import Settings
from app.utilities.client_user_id import (
    InvalidClientUserIDError,
    normalize_client_user_id,
)


def test_settings_parse_environment_values() -> None:
    settings = Settings.model_validate(
        {
            "APP_ENV": "staging",
            "LOG_LEVEL": "debug",
            "DEFAULT_CLIENT_USER_ID": "spendant-local-user",
            "PLAID_CLIENT_ID": "client-id",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "CORS_ORIGINS": "http://localhost:3000, https://staging.spendant.app",
            "API_PUBLIC_BASE_URL": "https://staging-api.spendant.app",
        }
    )

    assert settings.app_env == "staging"
    assert settings.log_level == "DEBUG"
    assert settings.default_client_user_id == "spendant-local-user"
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "https://staging.spendant.app",
    ]
    assert settings.api_public_base_url == "https://staging-api.spendant.app"


def test_settings_rejects_invalid_app_env() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "APP_ENV": "invalid",
                "PLAID_CLIENT_ID": "client-id",
                "PLAID_SECRET": "secret",
                "PLAID_ENV": "sandbox",
            }
        )


def test_settings_rejects_invalid_plaid_env() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "APP_ENV": "local",
                "PLAID_CLIENT_ID": "client-id",
                "PLAID_SECRET": "secret",
                "PLAID_ENV": "qa",
            }
        )


def test_normalize_client_user_id_accepts_uuid() -> None:
    value = "11111111-1111-1111-1111-111111111111"
    assert normalize_client_user_id(value) == value


def test_normalize_client_user_id_rejects_empty() -> None:
    with pytest.raises(InvalidClientUserIDError):
        normalize_client_user_id("   ")


def test_normalize_client_user_id_rejects_invalid_characters() -> None:
    with pytest.raises(InvalidClientUserIDError):
        normalize_client_user_id("bad user id!")
