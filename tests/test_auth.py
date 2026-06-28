from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.dashboard_service import DashboardService, get_dashboard_service
from tests.fakes import FakePlaidService


@pytest.fixture
def staging_settings() -> Settings:
    return Settings.model_validate(
        {
            "APP_ENV": "staging",
            "AUTH_REQUIRED": True,
            "AUTH_ISSUER": "https://auth.example.com/",
            "AUTH_AUDIENCE": "spendant-api",
            "AUTH_JWKS_URL": "https://auth.example.com/.well-known/jwks.json",
            "PLAID_CLIENT_ID": "client-id",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "API_PUBLIC_BASE_URL": "https://staging-api.spendant.app",
            "TOKEN_ENCRYPTION_KEY": "test-token-encryption-key",
        }
    )


@pytest.fixture
def staging_client(
    staging_settings: Settings,
    fake_plaid_service: FakePlaidService,
    snapshot_store: object,
) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: staging_settings
    app.dependency_overrides[get_dashboard_service] = lambda: DashboardService(
        plaid_service=fake_plaid_service,
        snapshot_store=snapshot_store,
    )
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_staging_requires_bearer_token(staging_client: TestClient) -> None:
    response = staging_client.get("/api/dashboard/summary")

    assert response.status_code == 401
    assert response.json()["error_code"] == "auth_required"


@patch("app.dependencies.validate_bearer_token", return_value="11111111-1111-1111-1111-111111111111")
def test_staging_accepts_valid_jwt(
    _mock_validate: object,
    staging_client: TestClient,
    fake_plaid_service: FakePlaidService,
) -> None:
    fake_plaid_service.accounts = []

    response = staging_client.get(
        "/api/dashboard/summary",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200


@patch("app.dependencies.validate_bearer_token", return_value="11111111-1111-1111-1111-111111111111")
def test_staging_rejects_mismatched_client_user_id(
    _mock_validate: object,
    staging_client: TestClient,
) -> None:
    response = staging_client.get(
        "/api/dashboard/summary",
        params={"client_user_id": "22222222-2222-2222-2222-222222222222"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "auth_forbidden"
