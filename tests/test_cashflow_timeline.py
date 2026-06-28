from datetime import date

from app.schemas.dashboard import NormalizedTransaction
from app.schemas.plaid import PlaidCreditCardLiability
from app.services.cashflow_timeline import build_cashflow_timeline, build_historical_timeline
from app.services.transaction_classifier import EXPENSES, INCOME, TRANSFER


def _transaction(
    *,
    transaction_id: str,
    amount: float,
    bucket: str,
    day: int,
    month: int | None = None,
    year: int | None = None,
) -> NormalizedTransaction:
    today = date.today()
    month = month or today.month
    year = year or today.year
    return NormalizedTransaction(
        transaction_id=transaction_id,
        account_id="checking-1",
        name=f"Transaction {transaction_id}",
        merchant_name=f"Merchant {transaction_id}",
        amount=amount,
        date=f"{year:04d}-{month:02d}-{day:02d}",
        bucket=bucket,
        pending=False,
    )


def test_build_cashflow_timeline_uses_lowest_balance_for_safe_to_move() -> None:
    today = date.today()
    posted = [
        _transaction(transaction_id="income", amount=-3000, bucket=INCOME, day=1),
        _transaction(transaction_id="rent", amount=1800, bucket="HOUSING", day=5),
        _transaction(transaction_id="groceries", amount=900, bucket=EXPENSES, day=10),
    ]

    timeline = build_cashflow_timeline(
        checking_balance=5000,
        protected_balance=500,
        recurring_streams=[],
        liabilities=[],
        posted_transactions=posted,
        current_month_transaction_ids={transaction.transaction_id for transaction in posted},
    )

    assert timeline.projected_end_balance >= timeline.lowest_projected_balance
    assert timeline.safe_to_move_today == max(0, timeline.lowest_projected_balance - 500)
    assert timeline.lowest_projected_balance_date is not None


def test_build_cashflow_timeline_projects_credit_card_obligation() -> None:
    today = date.today()
    due_date = today.replace(day=min(today.day + 5, 28)).isoformat()
    liability = PlaidCreditCardLiability(
        account_id="card-1",
        account_name="Chase Sapphire",
        current_balance=1200,
        last_statement_balance=900,
        minimum_payment_amount=35,
        next_payment_due_date=due_date,
    )

    timeline = build_cashflow_timeline(
        checking_balance=4000,
        protected_balance=100,
        recurring_streams=[],
        liabilities=[liability],
        posted_transactions=[],
        current_month_transaction_ids=set(),
    )

    assert len(timeline.credit_card_obligations) == 1
    assert timeline.credit_card_obligations[0].projected_payment_amount == 900
    assert any(event.source == "liability" for event in timeline.cash_flow_events)


def test_build_historical_timeline_replays_posted_transactions() -> None:
    today = date.today()
    if today.month == 1:
        month_year = today.year - 1
        month_month = 12
    else:
        month_year = today.year
        month_month = today.month - 1

    transactions = [
        _transaction(
            transaction_id="prev-income",
            amount=-2000,
            bucket=INCOME,
            day=5,
            month=month_month,
            year=month_year,
        ),
        _transaction(
            transaction_id="prev-rent",
            amount=1500,
            bucket="HOUSING",
            day=7,
            month=month_month,
            year=month_year,
        ),
        _transaction(
            transaction_id="future-income",
            amount=-1000,
            bucket=INCOME,
            day=5,
            month=today.month,
            year=today.year,
        ),
    ]

    timeline = build_historical_timeline(
        checking_balance=6000,
        protected_balance=200,
        all_posted_transactions=transactions,
        month_year=month_year,
        month_month=month_month,
    )

    assert timeline.cash_flow_events
    assert all(event.source == "posted" for event in timeline.cash_flow_events)
    assert timeline.safe_to_move_today >= 0
    assert timeline.projected_end_balance > 0
