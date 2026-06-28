from app.schemas.dashboard import DashboardSummaryResponse, MoneyDestinationSnapshot


def _sample_summary(*, month: str, destinations: list[MoneyDestinationSnapshot] | None = None) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        month=month,
        is_historical=True,
        snapshot_source="computed",
        checking_balance=5000,
        income_total=4000,
        housing_total=1500,
        expenses_total=800,
        subscriptions_total=100,
        transfer_total=300,
        income_posted_total=4000,
        housing_posted_total=1500,
        expenses_posted_total=800,
        subscriptions_posted_total=100,
        credit_card_payments_posted_total=300,
        income_upcoming_total=0,
        housing_upcoming_total=0,
        subscriptions_upcoming_total=0,
        credit_card_payments_upcoming_total=0,
        protected_balance=200,
        projected_month_end_balance=5200,
        safe_to_move_amount=1200,
        safe_to_move_today=1200,
        lowest_projected_balance=4800,
        lowest_projected_balance_date=f"{month}-15",
        transactions=[],
        recurring_streams=[],
        credit_card_obligations=[],
        cash_flow_events=[],
        money_destinations=destinations,
    )


def test_save_and_read_snapshot(snapshot_store) -> None:
    summary = _sample_summary(month="2026-05")
    saved = snapshot_store.save_snapshot(
        client_user_id="test-user",
        month="2026-05",
        summary=summary,
    )

    loaded = snapshot_store.get_snapshot(client_user_id="test-user", month="2026-05")

    assert loaded is not None
    assert loaded.snapshot_source == "stored"
    assert loaded.snapshot_finalized_at is not None
    assert saved.safe_to_move_amount == loaded.safe_to_move_amount


def test_upsert_snapshot_overwrites_existing_month(snapshot_store) -> None:
    snapshot_store.save_snapshot(
        client_user_id="test-user",
        month="2026-04",
        summary=_sample_summary(month="2026-04"),
    )
    updated = snapshot_store.save_snapshot(
        client_user_id="test-user",
        month="2026-04",
        summary=_sample_summary(
            month="2026-04",
            destinations=[
                MoneyDestinationSnapshot(
                    id="dest-1",
                    name="Savings Account",
                    percent=0.5,
                    icon="banknote.fill",
                )
            ],
        ),
    )

    loaded = snapshot_store.get_snapshot(client_user_id="test-user", month="2026-04")

    assert loaded is not None
    assert loaded.money_destinations is not None
    assert len(loaded.money_destinations) == 1
    assert updated.money_destinations[0].percent == 0.5


def test_list_snapshot_months_is_reverse_chronological(snapshot_store) -> None:
    snapshot_store.save_snapshot(
        client_user_id="test-user",
        month="2026-03",
        summary=_sample_summary(month="2026-03"),
    )
    snapshot_store.save_snapshot(
        client_user_id="test-user",
        month="2026-05",
        summary=_sample_summary(month="2026-05"),
    )

    months = snapshot_store.list_snapshot_months(client_user_id="test-user")

    assert months == ["2026-05", "2026-03"]
