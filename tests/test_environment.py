from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.config import Settings


def test_cors_disabled_by_default() -> None:
    settings = Settings.model_validate(
        {
            "APP_ENV": "local",
            "PLAID_CLIENT_ID": "client-id",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
        }
    )

    assert settings.cors_origin_list == []


def test_cors_enabled_when_configured() -> None:
    settings = Settings.model_validate(
        {
            "APP_ENV": "local",
            "PLAID_CLIENT_ID": "client-id",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "CORS_ORIGINS": "https://staging.spendant.app",
        }
    )

    app = FastAPI()
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get(
        "/ping",
        headers={"Origin": "https://staging.spendant.app"},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://staging.spendant.app"


def test_plaid_service_maps_development_environment() -> None:
    from app.services.plaid_service import PlaidService

    settings = Settings.model_validate(
        {
            "APP_ENV": "local",
            "PLAID_CLIENT_ID": "client-id",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "development",
        }
    )
    service = PlaidService(settings)

    assert service._plaid_host() == "https://development.plaid.com"
