from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.dashboard import DashboardSummaryResponse, MoneyDestinationSnapshot
from app.services.dashboard_service import DashboardService, get_dashboard_service
from tests.fakes import FakePlaidService, checking_account, plaid_transaction


CLIENT_USER_ID = "phase-one-route-user"
HISTORICAL_MONTH = "2026-05"


@pytest.fixture
def route_client(
    fake_plaid_service: FakePlaidService,
    snapshot_store: object,
) -> TestClient:
    service = DashboardService(
        plaid_service=fake_plaid_service,
        snapshot_store=snapshot_store,
    )
    app.dependency_overrides[get_dashboard_service] = lambda: service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _seed_current_month_transactions(fake_plaid_service: FakePlaidService) -> None:
    today = date.today()
    month_prefix = f"{today.year:04d}-{today.month:02d}"
    fake_plaid_service.accounts = [checking_account(4200)]
    fake_plaid_service.transactions = [
        plaid_transaction(
            transaction_id="route-income",
            amount=-2200,
            date=f"{month_prefix}-02",
            name="Payroll",
            primary="INCOME",
            detailed="INCOME_WAGES",
        )
    ]


def test_get_dashboard_summary_route(route_client: TestClient, fake_plaid_service: FakePlaidService) -> None:
    _seed_current_month_transactions(fake_plaid_service)

    response = route_client.get(
        "/api/dashboard/summary",
        params={"client_user_id": CLIENT_USER_ID},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_source"] == "live"
    assert payload["income_total"] == 2200


def test_get_dashboard_summary_with_month_query(
    route_client: TestClient,
    fake_plaid_service: FakePlaidService,
) -> None:
    fake_plaid_service.accounts = [checking_account(5000)]
    fake_plaid_service.transactions = [
        plaid_transaction(
            transaction_id="hist-income",
            amount=-1800,
            date=f"{HISTORICAL_MONTH}-03",
            name="Payroll",
            primary="INCOME",
            detailed="INCOME_WAGES",
        )
    ]

    response = route_client.get(
        "/api/dashboard/summary",
        params={
            "client_user_id": CLIENT_USER_ID,
            "month": HISTORICAL_MONTH,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["month"] == HISTORICAL_MONTH
    assert payload["is_historical"] is True
    assert payload["snapshot_source"] == "computed"


def test_finalize_dashboard_snapshot_route(
    route_client: TestClient,
    fake_plaid_service: FakePlaidService,
) -> None:
    fake_plaid_service.accounts = [checking_account(5000)]
    fake_plaid_service.transactions = [
        plaid_transaction(
            transaction_id="finalize-income",
            amount=-2000,
            date=f"{HISTORICAL_MONTH}-01",
            name="Payroll",
            primary="INCOME",
            detailed="INCOME_WAGES",
        )
    ]

    response = route_client.post(
        "/api/dashboard/snapshots/finalize",
        params={
            "client_user_id": CLIENT_USER_ID,
            "month": HISTORICAL_MONTH,
        },
        json={
            "protected_balance": 125,
            "money_destinations": [
                {
                    "id": "dest-1",
                    "name": "Savings Account",
                    "percent": 1.0,
                    "icon": "banknote.fill",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_source"] == "stored"
    assert payload["money_destinations"][0]["name"] == "Savings Account"


def test_finalize_current_month_returns_400(route_client: TestClient) -> None:
    today = date.today()
    current_month = f"{today.year:04d}-{today.month:02d}"

    response = route_client.post(
        "/api/dashboard/snapshots/finalize",
        params={
            "client_user_id": CLIENT_USER_ID,
            "month": current_month,
        },
        json={},
    )

    assert response.status_code == 400
    assert "Only completed months" in response.json()["detail"]


def test_invalid_client_user_id_returns_400(route_client: TestClient) -> None:
    response = route_client.get(
        "/api/dashboard/summary",
        params={"client_user_id": "bad user id"},
    )

    assert response.status_code == 400
    assert "client_user_id" in response.json()["detail"]
