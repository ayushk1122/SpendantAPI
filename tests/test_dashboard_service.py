from datetime import date

import pytest

from app.schemas.dashboard import DashboardSummaryResponse, MoneyDestinationSnapshot
from tests.fakes import FakePlaidService, checking_account, plaid_transaction


CLIENT_USER_ID = "phase-one-test-user"
HISTORICAL_MONTH = "2026-05"


def _historical_month() -> str:
    today = date.today()
    if today.month == 1:
        return f"{today.year - 1:12d}"
    return f"{today.year:04d}-{today.month - 1:02d}"


def _seed_current_month_transactions(fake_plaid_service: FakePlaidService) -> None:
    today = date.today()
    month_prefix = f"{today.year:04d}-{today.month:02d}"
    fake_plaid_service.accounts = [checking_account(5000)]
    fake_plaid_service.transactions = [
        plaid_transaction(
            transaction_id="income-1",
            amount=-3000,
            date=f"{month_prefix}-01",
            name="Payroll",
            primary="INCOME",
            detailed="INCOME_WAGES",
        ),
        plaid_transaction(
            transaction_id="rent-1",
            amount=1500,
            date=f"{month_prefix}-05",
            name="Rent",
            primary="RENT_AND_UTILITIES",
            detailed="RENT_AND_UTILITIES_RENT",
        ),
        plaid_transaction(
            transaction_id="coffee-1",
            amount=12.50,
            date=f"{month_prefix}-10",
            name="Coffee Shop",
            primary="FOOD_AND_DRINK",
            detailed="FOOD_AND_DRINK_COFFEE",
        ),
    ]


def _seed_historical_month_transactions(fake_plaid_service: FakePlaidService) -> None:
    fake_plaid_service.accounts = [checking_account(6000)]
    fake_plaid_service.transactions = [
        plaid_transaction(
            transaction_id="hist-income",
            amount=-2500,
            date=f"{HISTORICAL_MONTH}-01",
            name="Payroll",
            primary="INCOME",
            detailed="INCOME_WAGES",
        ),
        plaid_transaction(
            transaction_id="hist-rent",
            amount=1400,
            date=f"{HISTORICAL_MONTH}-05",
            name="Rent",
            primary="RENT_AND_UTILITIES",
            detailed="RENT_AND_UTILITIES_RENT",
        ),
    ]


def test_current_month_uses_live_computed_data(
    dashboard_service: object,
    fake_plaid_service: FakePlaidService,
) -> None:
    _seed_current_month_transactions(fake_plaid_service)

    summary = dashboard_service.get_dashboard_summary(CLIENT_USER_ID)

    assert summary.is_historical is False
    assert summary.snapshot_source == "live"
    assert summary.income_total > 0
    assert len(summary.transactions) >= 3


def test_historical_month_prefers_stored_snapshot(
    dashboard_service: object,
    fake_plaid_service: FakePlaidService,
    snapshot_store: object,
) -> None:
    stored = DashboardSummaryResponse(
        month=HISTORICAL_MONTH,
        is_historical=True,
        snapshot_source="stored",
        checking_balance=9999,
        income_total=1111,
        housing_total=222,
        expenses_total=33,
        subscriptions_total=4,
        transfer_total=5,
        income_posted_total=1111,
        housing_posted_total=222,
        expenses_posted_total=33,
        subscriptions_posted_total=4,
        credit_card_payments_posted_total=5,
        income_upcoming_total=0,
        housing_upcoming_total=0,
        subscriptions_upcoming_total=0,
        credit_card_payments_upcoming_total=0,
        protected_balance=100,
        projected_month_end_balance=9000,
        safe_to_move_amount=8900,
        safe_to_move_today=8900,
        lowest_projected_balance=8500,
        lowest_projected_balance_date=f"{HISTORICAL_MONTH}-20",
        transactions=[],
        recurring_streams=[],
        credit_card_obligations=[],
        cash_flow_events=[],
    )
    snapshot_store.save_snapshot(
        client_user_id=CLIENT_USER_ID,
        month=HISTORICAL_MONTH,
        summary=stored,
    )
    _seed_historical_month_transactions(fake_plaid_service)

    summary = dashboard_service.get_dashboard_summary(
        CLIENT_USER_ID,
        month=HISTORICAL_MONTH,
    )

    assert summary.snapshot_source == "stored"
    assert summary.checking_balance == 9999
    assert summary.income_total == 1111


def test_historical_month_falls_back_to_computed_summary(
    dashboard_service: object,
    fake_plaid_service: FakePlaidService,
) -> None:
    _seed_historical_month_transactions(fake_plaid_service)

    summary = dashboard_service.get_dashboard_summary(
        CLIENT_USER_ID,
        month=HISTORICAL_MONTH,
    )

    assert summary.snapshot_source == "computed"
    assert summary.is_historical is True
    assert summary.income_total == 2500
    assert summary.housing_total == 1400


def test_finalize_month_snapshot_rejects_current_month(
    dashboard_service: object,
) -> None:
    today = date.today()
    current_month = f"{today.year:04d}-{today.month:02d}"

    with pytest.raises(ValueError, match="Only completed months"):
        dashboard_service.finalize_month_snapshot(
            client_user_id=CLIENT_USER_ID,
            month=current_month,
        )


def test_finalize_month_snapshot_stores_money_destinations(
    dashboard_service: object,
    fake_plaid_service: FakePlaidService,
    snapshot_store: object,
) -> None:
    _seed_historical_month_transactions(fake_plaid_service)
    destinations = [
        MoneyDestinationSnapshot(
            id="dest-savings",
            name="Savings Account",
            percent=0.6,
            icon="banknote.fill",
        ),
        MoneyDestinationSnapshot(
            id="dest-invest",
            name="Investments",
            percent=0.4,
            icon="chart.pie.fill",
        ),
    ]

    saved = dashboard_service.finalize_month_snapshot(
        client_user_id=CLIENT_USER_ID,
        month=HISTORICAL_MONTH,
        protected_balance=150,
        money_destinations=destinations,
    )

    assert saved.snapshot_source == "stored"
    assert saved.money_destinations is not None
    assert len(saved.money_destinations) == 2
    assert saved.money_destinations[0].percent == 0.6

    loaded = snapshot_store.get_snapshot(
        client_user_id=CLIENT_USER_ID,
        month=HISTORICAL_MONTH,
    )
    assert loaded is not None
    assert loaded.money_destinations == destinations
