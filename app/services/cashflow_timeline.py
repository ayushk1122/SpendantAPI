from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from app.schemas.dashboard import (
    CashFlowEvent,
    CreditCardObligation,
    NormalizedTransaction,
    RecurringStream,
)
from app.schemas.plaid import PlaidCreditCardLiability
from app.services.transaction_classifier import INCOME, TRANSFER


@dataclass(frozen=True)
class TimelineSummary:
    cash_flow_events: list[CashFlowEvent]
    credit_card_obligations: list[CreditCardObligation]
    projected_end_balance: float
    safe_to_move_today: float
    lowest_projected_balance: float
    lowest_projected_balance_date: str | None


def build_cashflow_timeline(
    *,
    checking_balance: float,
    protected_balance: float,
    recurring_streams: list[RecurringStream],
    liabilities: list[PlaidCreditCardLiability],
    posted_transactions: list[NormalizedTransaction],
    current_month_transaction_ids: set[str],
) -> TimelineSummary:
    today = date.today()
    horizon_end = _horizon_end(today, liabilities)
    posted_transfers = [
        transaction
        for transaction in posted_transactions
        if transaction.bucket == TRANSFER
    ]

    credit_card_obligations = _build_credit_card_obligations(
        liabilities=liabilities,
        posted_transfers=posted_transfers,
        today=today,
    )
    events = _build_future_events(
        recurring_streams=recurring_streams,
        credit_card_obligations=credit_card_obligations,
        current_month_transaction_ids=current_month_transaction_ids,
        today=today,
        horizon_end=horizon_end,
    )
    lowest_balance, lowest_date, projected_end_balance = _project_balances(
        starting_balance=checking_balance,
        events=events,
        today=today,
        horizon_end=horizon_end,
    )
    safe_to_move_today = round(max(0, lowest_balance - protected_balance), 2)

    return TimelineSummary(
        cash_flow_events=sorted(events, key=lambda event: (event.date, event.label)),
        credit_card_obligations=credit_card_obligations,
        projected_end_balance=round(projected_end_balance, 2),
        safe_to_move_today=safe_to_move_today,
        lowest_projected_balance=round(lowest_balance, 2),
        lowest_projected_balance_date=lowest_date.isoformat() if lowest_date else None,
    )


def _horizon_end(today: date, liabilities: list[PlaidCreditCardLiability]) -> date:
    month_end = today.replace(
        day=calendar.monthrange(today.year, today.month)[1]
    )
    latest_due = month_end

    for liability in liabilities:
        due_date = _parse_date(liability.next_payment_due_date)
        if due_date and due_date >= today and due_date > latest_due:
            latest_due = due_date

    return latest_due


def _build_credit_card_obligations(
    *,
    liabilities: list[PlaidCreditCardLiability],
    posted_transfers: list[NormalizedTransaction],
    today: date,
) -> list[CreditCardObligation]:
    obligations: list[CreditCardObligation] = []

    for liability in liabilities:
        projected_payment = _projected_payment_amount(liability)
        is_already_paid = _card_payment_already_posted(
            liability=liability,
            posted_transfers=posted_transfers,
            today=today,
        )
        obligations.append(
            CreditCardObligation(
                account_id=liability.account_id,
                account_name=liability.account_name or "Credit Card",
                institution_name=liability.institution_name,
                current_balance=liability.current_balance,
                last_statement_balance=liability.last_statement_balance,
                minimum_payment_amount=liability.minimum_payment_amount,
                next_payment_due_date=liability.next_payment_due_date,
                last_statement_issue_date=liability.last_statement_issue_date,
                last_payment_amount=liability.last_payment_amount,
                last_payment_date=liability.last_payment_date,
                projected_payment_amount=projected_payment,
                payment_strategy="statement_balance",
                is_already_paid_this_cycle=is_already_paid,
            )
        )

    return obligations


def _projected_payment_amount(liability: PlaidCreditCardLiability) -> float:
    if liability.last_statement_balance and liability.last_statement_balance > 0:
        return round(float(liability.last_statement_balance), 2)

    if liability.minimum_payment_amount and liability.minimum_payment_amount > 0:
        return round(float(liability.minimum_payment_amount), 2)

    if liability.current_balance and liability.current_balance > 0:
        return round(float(liability.current_balance), 2)

    return 0.0


def _card_payment_already_posted(
    *,
    liability: PlaidCreditCardLiability,
    posted_transfers: list[NormalizedTransaction],
    today: date,
) -> bool:
    last_payment_date = _parse_date(liability.last_payment_date)
    if last_payment_date and _is_current_month(last_payment_date, today):
        return True

    due_date = _parse_date(liability.next_payment_due_date)
    for transfer in posted_transfers:
        transfer_date = _parse_date(transfer.date)
        if not transfer_date or not _is_current_month(transfer_date, today):
            continue

        if due_date and abs((transfer_date - due_date).days) <= 7:
            return True

        projected_payment = _projected_payment_amount(liability)
        if projected_payment > 0 and abs(transfer.amount - projected_payment) <= 25:
            return True

    return False


def _build_future_events(
    *,
    recurring_streams: list[RecurringStream],
    credit_card_obligations: list[CreditCardObligation],
    current_month_transaction_ids: set[str],
    today: date,
    horizon_end: date,
) -> list[CashFlowEvent]:
    events: list[CashFlowEvent] = []
    has_liability_card_payments = any(
        obligation.projected_payment_amount > 0
        and not obligation.is_already_paid_this_cycle
        for obligation in credit_card_obligations
    )

    for stream in recurring_streams:
        if stream.bucket == TRANSFER and has_liability_card_payments:
            continue

        event_date = _parse_date(stream.predicted_next_date)
        if not event_date or event_date < today or event_date > horizon_end:
            continue

        if any(
            transaction_id in current_month_transaction_ids
            for transaction_id in stream.transaction_ids
        ):
            continue

        amount = stream.last_amount or stream.average_amount or 0
        if stream.bucket == INCOME:
            signed_amount = abs(amount)
        else:
            signed_amount = -abs(amount)

        events.append(
            CashFlowEvent(
                date=event_date.isoformat(),
                amount=round(signed_amount, 2),
                bucket=stream.bucket,
                label=stream.description,
                account_id=stream.account_id,
                source="recurring",
            )
        )

    for obligation in credit_card_obligations:
        if obligation.is_already_paid_this_cycle:
            continue

        due_date = _parse_date(obligation.next_payment_due_date)
        if not due_date or due_date < today or due_date > horizon_end:
            continue

        if obligation.projected_payment_amount <= 0:
            continue

        events.append(
            CashFlowEvent(
                date=due_date.isoformat(),
                amount=round(-obligation.projected_payment_amount, 2),
                bucket=TRANSFER,
                label=f"{obligation.account_name} payment",
                account_id=obligation.account_id,
                source="liability",
            )
        )

    return events


def _project_balances(
    *,
    starting_balance: float,
    events: list[CashFlowEvent],
    today: date,
    horizon_end: date,
) -> tuple[float, date | None, float]:
    events_by_date: dict[date, list[CashFlowEvent]] = {}
    for event in events:
        event_date = _parse_date(event.date)
        if not event_date:
            continue
        events_by_date.setdefault(event_date, []).append(event)

    balance = starting_balance
    lowest_balance = balance
    lowest_date = today

    current_day = today
    while current_day <= horizon_end:
        for event in events_by_date.get(current_day, []):
            balance += event.amount

        if balance < lowest_balance:
            lowest_balance = balance
            lowest_date = current_day

        current_day += timedelta(days=1)

    return lowest_balance, lowest_date, balance


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _is_current_month(value: date, today: date) -> bool:
    return value.year == today.year and value.month == today.month


def build_historical_timeline(
    *,
    checking_balance: float,
    protected_balance: float,
    all_posted_transactions: list[NormalizedTransaction],
    month_year: int,
    month_month: int,
) -> TimelineSummary:
    month_start = date(month_year, month_month, 1)
    month_end = month_start.replace(
        day=calendar.monthrange(month_year, month_month)[1]
    )
    net_from_month_start = _net_flow_since(
        all_posted_transactions,
        since=month_start,
    )
    starting_balance = checking_balance - net_from_month_start

    month_transactions = [
        transaction
        for transaction in all_posted_transactions
        if _is_in_month(transaction.date, month_year, month_month)
    ]
    events = [
        CashFlowEvent(
            date=transaction.date,
            amount=_transaction_signed_amount(transaction),
            bucket=transaction.bucket,
            label=transaction.merchant_name or transaction.name,
            account_id=transaction.account_id,
            source="posted",
        )
        for transaction in month_transactions
    ]

    events_by_day: dict[date, list[CashFlowEvent]] = defaultdict(list)
    for event in events:
        event_date = _parse_date(event.date)
        if event_date:
            events_by_day[event_date].append(event)

    balance = starting_balance
    lowest_balance = balance
    lowest_date: date | None = month_start
    current_day = month_start

    while current_day <= month_end:
        for event in events_by_day.get(current_day, []):
            balance += event.amount

        if balance < lowest_balance:
            lowest_balance = balance
            lowest_date = current_day

        current_day += timedelta(days=1)

    month_end_balance = balance
    safe_to_move_amount = round(max(0, month_end_balance - protected_balance), 2)

    return TimelineSummary(
        cash_flow_events=sorted(events, key=lambda event: (event.date, event.label)),
        credit_card_obligations=[],
        projected_end_balance=round(month_end_balance, 2),
        safe_to_move_today=safe_to_move_amount,
        lowest_projected_balance=round(lowest_balance, 2),
        lowest_projected_balance_date=lowest_date.isoformat() if lowest_date else None,
    )


def _transaction_signed_amount(transaction: NormalizedTransaction) -> float:
    if transaction.bucket == INCOME:
        return abs(transaction.amount)

    return -abs(transaction.amount)


def _net_flow_since(
    transactions: list[NormalizedTransaction],
    *,
    since: date,
    until: date | None = None,
) -> float:
    total = 0.0

    for transaction in transactions:
        transaction_date = _parse_date(transaction.date)
        if not transaction_date or transaction_date < since:
            continue
        if until and transaction_date > until:
            continue

        total += _transaction_signed_amount(transaction)

    return total


def _is_in_month(value: str | None, year: int, month: int) -> bool:
    transaction_date = _parse_date(value)
    if not transaction_date:
        return False

    return transaction_date.year == year and transaction_date.month == month
