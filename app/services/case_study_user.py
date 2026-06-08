import json
from datetime import date
from pathlib import Path

from app.schemas.dashboard import (
    CashFlowEvent,
    CreditCardObligation,
    DashboardSummaryResponse,
    NormalizedTransaction,
    RecurringStream,
)
from app.services.cashflow_timeline import build_historical_timeline
from app.services.transaction_classifier import (
    EXPENSES,
    HOUSING,
    INCOME,
    SUBSCRIPTIONS,
    TRANSFER,
)

CASE_STUDY_PATH = Path("data/case_study_user.json")


def get_case_study_dashboard(
    *,
    client_user_id: str,
    protected_balance: float,
    month: str | None = None,
    is_historical: bool = False,
) -> DashboardSummaryResponse | None:
    if not CASE_STUDY_PATH.exists():
        return None

    payload = json.loads(CASE_STUDY_PATH.read_text())
    if payload.get("client_user_id") != client_user_id:
        return None

    checking_balance = float(payload["checking_balance"])
    all_transactions = [
        NormalizedTransaction(**transaction)
        for transaction in payload.get("transactions", [])
    ]
    month_year, month_month = _parse_month_value(month)
    transactions = [
        transaction
        for transaction in all_transactions
        if _is_in_month(transaction.date, month_year, month_month)
    ]
    credit_card_obligations = [
        CreditCardObligation(**obligation)
        for obligation in payload.get("credit_card_obligations", [])
    ]
    all_cash_flow_events = [
        CashFlowEvent(**event)
        for event in payload.get("cash_flow_events", [])
    ]
    cash_flow_events = (
        [
            event
            for event in all_cash_flow_events
            if _is_in_month(event.date, month_year, month_month)
        ]
        if is_historical
        else all_cash_flow_events
    )
    recurring_streams = [
        RecurringStream(**stream)
        for stream in payload.get("recurring_streams", [])
    ]

    if is_historical:
        timeline = build_historical_timeline(
            checking_balance=checking_balance,
            protected_balance=protected_balance,
            all_posted_transactions=all_transactions,
            month_year=month_year,
            month_month=month_month,
        )
        income_posted_total = _posted_total(transactions, INCOME)
        housing_posted_total = _posted_total(transactions, HOUSING)
        expenses_posted_total = _posted_total(transactions, EXPENSES)
        subscriptions_posted_total = _posted_total(transactions, SUBSCRIPTIONS)
        card_payments_posted_total = _posted_total(transactions, TRANSFER)

        return DashboardSummaryResponse(
            month=month,
            is_historical=True,
            checking_balance=checking_balance,
            income_total=round(income_posted_total, 2),
            housing_total=round(housing_posted_total, 2),
            expenses_total=round(expenses_posted_total, 2),
            subscriptions_total=round(subscriptions_posted_total, 2),
            transfer_total=round(card_payments_posted_total, 2),
            income_posted_total=round(income_posted_total, 2),
            housing_posted_total=round(housing_posted_total, 2),
            expenses_posted_total=round(expenses_posted_total, 2),
            subscriptions_posted_total=round(subscriptions_posted_total, 2),
            credit_card_payments_posted_total=round(card_payments_posted_total, 2),
            income_upcoming_total=0,
            housing_upcoming_total=0,
            subscriptions_upcoming_total=0,
            credit_card_payments_upcoming_total=0,
            protected_balance=protected_balance,
            projected_month_end_balance=timeline.projected_end_balance,
            safe_to_move_amount=timeline.safe_to_move_today,
            safe_to_move_today=timeline.safe_to_move_today,
            lowest_projected_balance=timeline.lowest_projected_balance,
            lowest_projected_balance_date=timeline.lowest_projected_balance_date,
            transactions=transactions,
            recurring_streams=[],
            credit_card_obligations=[],
            cash_flow_events=timeline.cash_flow_events,
        )

    income_posted_total = _posted_total(transactions, INCOME)
    housing_posted_total = _posted_total(transactions, HOUSING)
    expenses_posted_total = _posted_total(transactions, EXPENSES)
    subscriptions_posted_total = _posted_total(transactions, SUBSCRIPTIONS)
    card_payments_posted_total = _posted_total(transactions, TRANSFER)

    income_upcoming_total = _event_total(cash_flow_events, INCOME)
    housing_upcoming_total = abs(_event_total(cash_flow_events, HOUSING))
    subscriptions_upcoming_total = abs(_event_total(cash_flow_events, SUBSCRIPTIONS))
    card_payments_upcoming_total = sum(
        obligation.projected_payment_amount
        for obligation in credit_card_obligations
        if not obligation.is_already_paid_this_cycle
    )

    projected_end_balance = _project_balance(checking_balance, cash_flow_events)
    lowest_balance, lowest_date = _lowest_balance(checking_balance, cash_flow_events)
    safe_to_move_today = round(max(0, lowest_balance - protected_balance), 2)
    safe_to_move_amount = round(max(0, projected_end_balance - protected_balance), 2)

    return DashboardSummaryResponse(
        month=month,
        is_historical=False,
        checking_balance=checking_balance,
        income_total=round(income_posted_total + income_upcoming_total, 2),
        housing_total=round(housing_posted_total + housing_upcoming_total, 2),
        expenses_total=round(expenses_posted_total, 2),
        subscriptions_total=round(
            subscriptions_posted_total + subscriptions_upcoming_total,
            2,
        ),
        transfer_total=round(
            card_payments_posted_total + card_payments_upcoming_total,
            2,
        ),
        income_posted_total=round(income_posted_total, 2),
        housing_posted_total=round(housing_posted_total, 2),
        expenses_posted_total=round(expenses_posted_total, 2),
        subscriptions_posted_total=round(subscriptions_posted_total, 2),
        credit_card_payments_posted_total=round(card_payments_posted_total, 2),
        income_upcoming_total=round(income_upcoming_total, 2),
        housing_upcoming_total=round(housing_upcoming_total, 2),
        subscriptions_upcoming_total=round(subscriptions_upcoming_total, 2),
        credit_card_payments_upcoming_total=round(card_payments_upcoming_total, 2),
        protected_balance=protected_balance,
        projected_month_end_balance=round(projected_end_balance, 2),
        safe_to_move_amount=safe_to_move_amount,
        safe_to_move_today=safe_to_move_today,
        lowest_projected_balance=round(lowest_balance, 2),
        lowest_projected_balance_date=lowest_date,
        transactions=transactions,
        recurring_streams=recurring_streams,
        credit_card_obligations=credit_card_obligations,
        cash_flow_events=sorted(cash_flow_events, key=lambda event: (event.date, event.label)),
    )


def _parse_month_value(month: str | None) -> tuple[int, int]:
    today = date.today()
    if not month:
        return today.year, today.month

    year_text, month_text = month.split("-", 1)
    return int(year_text), int(month_text)


def _is_in_month(value: str | None, year: int, month: int) -> bool:
    if not value:
        return False

    try:
        transaction_date = date.fromisoformat(value)
    except ValueError:
        return False

    return transaction_date.year == year and transaction_date.month == month


def _posted_total(transactions: list[NormalizedTransaction], bucket: str) -> float:
    matching = [transaction for transaction in transactions if transaction.bucket == bucket]
    if bucket == INCOME:
        return sum(abs(transaction.amount) for transaction in matching)

    return sum(transaction.amount for transaction in matching)


def _event_total(events: list[CashFlowEvent], bucket: str) -> float:
    return sum(event.amount for event in events if event.bucket == bucket)


def _project_balance(starting_balance: float, events: list[CashFlowEvent]) -> float:
    return round(starting_balance + sum(event.amount for event in events), 2)


def _lowest_balance(
    starting_balance: float,
    events: list[CashFlowEvent],
) -> tuple[float, str | None]:
    balance = starting_balance
    lowest_balance = balance
    lowest_date = date.today().isoformat()

    for event in sorted(events, key=lambda item: item.date):
        balance += event.amount
        if balance < lowest_balance:
            lowest_balance = balance
            lowest_date = event.date

    return lowest_balance, lowest_date
