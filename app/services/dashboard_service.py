import logging
import calendar
from datetime import date

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.case_study_user import get_case_study_dashboard
from app.schemas.plaid import PlaidCreditCardLiability
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    MoneyDestinationSnapshot,
    NormalizedTransaction,
    RecurringStream,
)
from app.services.cashflow_timeline import (
    build_cashflow_timeline,
    build_historical_timeline,
)
from app.services.dashboard_snapshot_store import DashboardSnapshotStore
from app.services.plaid_service import ExternalServiceError, PlaidItemNotFoundError, PlaidService
from app.services.transaction_classifier import (
    EXPENSES,
    HOUSING,
    INCOME,
    SUBSCRIPTIONS,
    TRANSFER,
    classify_transaction,
    is_subscription_like,
)

logger = logging.getLogger(__name__)

PROTECTED_BALANCE_DEFAULT = 30.0

UPCOMING_RECURRING_BUCKETS = {SUBSCRIPTIONS, HOUSING, INCOME, TRANSFER}


class DashboardService:
    def __init__(
        self,
        plaid_service: PlaidService,
        snapshot_store: DashboardSnapshotStore,
    ) -> None:
        self.plaid_service = plaid_service
        self.snapshot_store = snapshot_store

    def get_dashboard_summary(
        self,
        client_user_id: str,
        protected_balance: float | None = None,
        month: str | None = None,
    ) -> DashboardSummaryResponse:
        month_year, month_month, month_value, is_historical = _parse_dashboard_month(
            month
        )
        if is_historical:
            snapshot = self.snapshot_store.get_snapshot(
                client_user_id=client_user_id,
                month=month_value,
            )
            if snapshot:
                logger.info(
                    "dashboard snapshot hit client_user_id=%s month=%s",
                    client_user_id,
                    month_value,
                )
                return snapshot

        return self._build_dashboard_summary(
            client_user_id=client_user_id,
            protected_balance=protected_balance,
            month_year=month_year,
            month_month=month_month,
            month_value=month_value,
            is_historical=is_historical,
        )

    def finalize_month_snapshot(
        self,
        *,
        client_user_id: str,
        month: str,
        protected_balance: float | None = None,
        money_destinations: list[MoneyDestinationSnapshot] | None = None,
    ) -> DashboardSummaryResponse:
        month_year, month_month, month_value, is_historical = _parse_dashboard_month(
            month
        )
        if not is_historical:
            raise ValueError("Only completed months can be finalized as snapshots.")

        summary = self._build_dashboard_summary(
            client_user_id=client_user_id,
            protected_balance=protected_balance,
            month_year=month_year,
            month_month=month_month,
            month_value=month_value,
            is_historical=True,
            money_destinations=money_destinations,
        )
        saved = self.snapshot_store.save_snapshot(
            client_user_id=client_user_id,
            month=month_value,
            summary=summary,
        )
        logger.info(
            "dashboard snapshot finalized client_user_id=%s month=%s",
            client_user_id,
            month_value,
        )
        return saved

    def list_snapshot_months(self, *, client_user_id: str) -> list[str]:
        return self.snapshot_store.list_snapshot_months(client_user_id=client_user_id)

    def _build_dashboard_summary(
        self,
        *,
        client_user_id: str,
        protected_balance: float | None,
        month_year: int,
        month_month: int,
        month_value: str,
        is_historical: bool,
        money_destinations: list[MoneyDestinationSnapshot] | None = None,
    ) -> DashboardSummaryResponse:
        case_study = get_case_study_dashboard(
            client_user_id=client_user_id,
            protected_balance=protected_balance or PROTECTED_BALANCE_DEFAULT,
            month=month_value,
            is_historical=is_historical,
        )
        if case_study:
            return case_study

        accounts_response = self.plaid_service.get_accounts(client_user_id)
        transactions_response = self.plaid_service.get_transactions(client_user_id)

        transactions = [
            transaction.model_dump()
            for transaction in transactions_response.transactions
        ]
        recurring_streams = self._get_recurring_streams(client_user_id)
        recurring_bucket_by_transaction_id = _recurring_bucket_by_transaction_id(
            recurring_streams
        )
        month_transactions = [
            transaction
            for transaction in transactions
            if _is_in_month(transaction.get("date"), month_year, month_month)
        ]

        all_posted_transactions = [
            self._normalize_transaction(
                transaction,
                recurring_bucket_by_transaction_id.get(transaction["transaction_id"]),
            )
            for transaction in transactions
        ]
        posted_transactions = [
            self._normalize_transaction(
                transaction,
                recurring_bucket_by_transaction_id.get(transaction["transaction_id"]),
            )
            for transaction in month_transactions
        ]
        month_transaction_ids = {
            transaction["transaction_id"]
            for transaction in month_transactions
        }
        upcoming_recurring_totals = (
            {
                INCOME: 0.0,
                HOUSING: 0.0,
                EXPENSES: 0.0,
                SUBSCRIPTIONS: 0.0,
                TRANSFER: 0.0,
            }
            if is_historical
            else _upcoming_recurring_totals(
                recurring_streams,
                month_transaction_ids,
                month_year=month_year,
                month_month=month_month,
            )
        )

        income_posted_total = _posted_total(posted_transactions, INCOME)
        housing_posted_total = _posted_total(posted_transactions, HOUSING)
        expenses_posted_total = _posted_total(posted_transactions, EXPENSES)
        subscriptions_posted_total = _posted_total(posted_transactions, SUBSCRIPTIONS)
        credit_card_payments_posted_total = _posted_total(posted_transactions, TRANSFER)

        income_upcoming_total = upcoming_recurring_totals[INCOME]
        housing_upcoming_total = upcoming_recurring_totals[HOUSING]
        subscriptions_upcoming_total = upcoming_recurring_totals[SUBSCRIPTIONS]
        credit_card_payments_upcoming_total = upcoming_recurring_totals[TRANSFER]

        income_total = round(income_posted_total + income_upcoming_total, 2)
        housing_total = round(housing_posted_total + housing_upcoming_total, 2)
        expenses_total = round(expenses_posted_total, 2)
        subscriptions_total = round(
            subscriptions_posted_total + subscriptions_upcoming_total,
            2,
        )
        transfer_total = round(
            credit_card_payments_posted_total + credit_card_payments_upcoming_total,
            2,
        )

        checking_balance = _find_checking_balance(
            [account.model_dump() for account in accounts_response.accounts]
        )
        protected_balance = protected_balance or PROTECTED_BALANCE_DEFAULT

        if is_historical:
            timeline = build_historical_timeline(
                checking_balance=checking_balance,
                protected_balance=protected_balance,
                all_posted_transactions=all_posted_transactions,
                month_year=month_year,
                month_month=month_month,
            )
        else:
            liabilities = self._get_credit_card_liabilities(client_user_id)
            if not liabilities:
                liabilities = _fallback_liabilities_from_accounts(
                    [account.model_dump() for account in accounts_response.accounts]
                )
            liabilities = _dedupe_liabilities(liabilities)
            timeline = build_cashflow_timeline(
                checking_balance=checking_balance,
                protected_balance=protected_balance,
                recurring_streams=recurring_streams,
                liabilities=liabilities,
                posted_transactions=posted_transactions,
                current_month_transaction_ids=month_transaction_ids,
            )
        projected_month_end_balance = timeline.projected_end_balance
        safe_to_move_amount = round(
            max(0, projected_month_end_balance - protected_balance),
            2,
        )

        logger.info(
            "dashboard summary client_user_id=%s month=%s fetched_transactions=%s month_transactions=%s",
            client_user_id,
            month_value,
            len(transactions),
            len(month_transactions),
        )
        logger.info(
            "dashboard recurring client_user_id=%s active_streams=%s upcoming_totals=%s",
            client_user_id,
            len(recurring_streams),
            upcoming_recurring_totals,
        )
        logger.info(
            "dashboard totals client_user_id=%s income=%s housing=%s expenses_posted=%s subscriptions=%s card_payments=%s safe_to_move=%s",
            client_user_id,
            income_total,
            housing_total,
            expenses_posted_total,
            subscriptions_total,
            transfer_total,
            safe_to_move_amount,
        )
        logger.info(
            "dashboard timeline client_user_id=%s safe_to_move_today=%s lowest_balance=%s lowest_date=%s card_obligations=%s events=%s",
            client_user_id,
            timeline.safe_to_move_today,
            timeline.lowest_projected_balance,
            timeline.lowest_projected_balance_date,
            len(timeline.credit_card_obligations),
            len(timeline.cash_flow_events),
        )

        return DashboardSummaryResponse(
            month=month_value,
            is_historical=is_historical,
            snapshot_source="computed" if is_historical else "live",
            checking_balance=checking_balance,
            income_total=income_total,
            housing_total=housing_total,
            expenses_total=expenses_total,
            subscriptions_total=subscriptions_total,
            transfer_total=transfer_total,
            income_posted_total=round(income_posted_total, 2),
            housing_posted_total=round(housing_posted_total, 2),
            expenses_posted_total=round(expenses_posted_total, 2),
            subscriptions_posted_total=round(subscriptions_posted_total, 2),
            credit_card_payments_posted_total=round(credit_card_payments_posted_total, 2),
            income_upcoming_total=round(income_upcoming_total, 2),
            housing_upcoming_total=round(housing_upcoming_total, 2),
            subscriptions_upcoming_total=round(subscriptions_upcoming_total, 2),
            credit_card_payments_upcoming_total=round(
                credit_card_payments_upcoming_total,
                2,
            ),
            protected_balance=protected_balance,
            projected_month_end_balance=projected_month_end_balance,
            safe_to_move_amount=safe_to_move_amount,
            safe_to_move_today=timeline.safe_to_move_today,
            lowest_projected_balance=timeline.lowest_projected_balance,
            lowest_projected_balance_date=timeline.lowest_projected_balance_date,
            transactions=posted_transactions,
            recurring_streams=(
                []
                if is_historical
                else _upcoming_streams_for_month(
                    recurring_streams,
                    month_transaction_ids,
                    month_year=month_year,
                    month_month=month_month,
                )
            ),
            credit_card_obligations=timeline.credit_card_obligations,
            cash_flow_events=timeline.cash_flow_events,
            money_destinations=money_destinations,
        )

    def _normalize_transaction(
        self,
        transaction: dict,
        recurring_bucket: str | None = None,
    ) -> NormalizedTransaction:
        bucket = recurring_bucket or classify_transaction(transaction)
        if recurring_bucket is None and bucket == EXPENSES and is_subscription_like(transaction):
            bucket = SUBSCRIPTIONS

        return NormalizedTransaction(
            transaction_id=transaction["transaction_id"],
            account_id=transaction.get("account_id"),
            name=transaction["name"],
            merchant_name=transaction.get("merchant_name"),
            amount=transaction["amount"],
            date=transaction["date"],
            bucket=bucket,
            pending=transaction.get("pending", False),
            plaid_primary_category=transaction.get("plaid_primary_category"),
            plaid_detailed_category=transaction.get("plaid_detailed_category"),
            plaid_category_confidence=transaction.get("plaid_category_confidence"),
        )

    def _get_credit_card_liabilities(self, client_user_id: str) -> list:
        try:
            response = self.plaid_service.get_liabilities(client_user_id)
        except (ExternalServiceError, PlaidItemNotFoundError) as exc:
            logger.warning(
                "liabilities unavailable client_user_id=%s error=%s",
                client_user_id,
                exc,
            )
            return []

        return response.credit_cards

    def _get_recurring_streams(self, client_user_id: str) -> list[RecurringStream]:
        try:
            response = self.plaid_service.get_recurring_transactions(client_user_id)
        except ExternalServiceError as exc:
            logger.warning(
                "recurring transactions unavailable client_user_id=%s error=%s",
                client_user_id,
                exc,
            )
            return []

        inflow_streams = response.get("inflow_streams") or []
        outflow_streams = response.get("outflow_streams") or []
        return [
            _normalize_recurring_stream(stream)
            for stream in [*inflow_streams, *outflow_streams]
            if stream.get("is_active", False)
        ]


def get_dashboard_service(settings: Settings = Depends(get_settings)) -> DashboardService:
    return DashboardService(
        plaid_service=PlaidService(settings),
        snapshot_store=DashboardSnapshotStore(settings.plaid_storage_path),
    )


def _posted_total(transactions: list[NormalizedTransaction], bucket: str) -> float:
    matching = [transaction for transaction in transactions if transaction.bucket == bucket]
    if bucket == INCOME:
        return sum(abs(transaction.amount) for transaction in matching)

    return sum(transaction.amount for transaction in matching)


def _find_checking_balance(accounts: list[dict]) -> float:
    total = 0.0
    for account in accounts:
        if account.get("type") == "depository" and account.get("subtype") == "checking":
            total += float(
                account.get("balance")
                or account.get("current")
                or account.get("available_balance")
                or 0
            )

    return round(total, 2)


def _parse_dashboard_month(
    month: str | None,
) -> tuple[int, int, str, bool]:
    today = date.today()

    if not month:
        return today.year, today.month, f"{today.year:04d}-{today.month:02d}", False

    try:
        year_text, month_text = month.split("-", 1)
        month_year = int(year_text)
        month_month = int(month_text)
    except ValueError as exc:
        raise ValueError("month must use YYYY-MM format") from exc

    if month_month < 1 or month_month > 12:
        raise ValueError("month must use a valid calendar month")

    month_value = f"{month_year:04d}-{month_month:02d}"
    is_historical = (month_year, month_month) < (today.year, today.month)
    return month_year, month_month, month_value, is_historical


def _is_in_month(value: str | None, year: int, month: int) -> bool:
    if not value:
        return False

    try:
        transaction_date = date.fromisoformat(value)
    except ValueError:
        return False

    return transaction_date.year == year and transaction_date.month == month


def _normalize_recurring_stream(stream: dict) -> RecurringStream:
    personal_finance_category = stream.get("personal_finance_category") or {}
    last_amount = stream.get("last_amount") or {}
    average_amount = stream.get("average_amount") or {}
    transaction = {
        "amount": last_amount.get("amount") or average_amount.get("amount") or 0,
        "name": stream.get("description"),
        "merchant_name": stream.get("merchant_name"),
        "plaid_primary_category": personal_finance_category.get("primary"),
        "plaid_detailed_category": personal_finance_category.get("detailed"),
    }
    bucket = classify_transaction(transaction)
    if bucket == EXPENSES and is_subscription_like(transaction):
        bucket = SUBSCRIPTIONS

    return RecurringStream(
        stream_id=stream["stream_id"],
        account_id=stream.get("account_id"),
        description=stream["description"],
        merchant_name=stream.get("merchant_name"),
        bucket=bucket,
        frequency=_stringify(stream.get("frequency")),
        status=_stringify(stream.get("status")),
        is_active=stream.get("is_active", False),
        average_amount=average_amount.get("amount"),
        last_amount=last_amount.get("amount"),
        first_date=_stringify(stream.get("first_date")),
        last_date=_stringify(stream.get("last_date")),
        predicted_next_date=_stringify(stream.get("predicted_next_date")),
        transaction_ids=stream.get("transaction_ids") or [],
        plaid_primary_category=personal_finance_category.get("primary"),
        plaid_detailed_category=personal_finance_category.get("detailed"),
        plaid_category_confidence=personal_finance_category.get("confidence_level"),
    )


def _recurring_bucket_by_transaction_id(
    streams: list[RecurringStream],
) -> dict[str, str]:
    bucket_by_transaction_id: dict[str, str] = {}
    for stream in streams:
        if stream.bucket not in {SUBSCRIPTIONS, HOUSING, INCOME, TRANSFER}:
            continue

        for transaction_id in stream.transaction_ids:
            bucket_by_transaction_id[transaction_id] = stream.bucket
    return bucket_by_transaction_id


def _stream_already_posted_this_month(
    stream: RecurringStream,
    current_month_transaction_ids: set[str],
) -> bool:
    return any(
        transaction_id in current_month_transaction_ids
        for transaction_id in stream.transaction_ids
    )


def _upcoming_recurring_totals(
    streams: list[RecurringStream],
    current_month_transaction_ids: set[str],
    *,
    month_year: int,
    month_month: int,
) -> dict[str, float]:
    totals = {
        INCOME: 0.0,
        HOUSING: 0.0,
        EXPENSES: 0.0,
        SUBSCRIPTIONS: 0.0,
        TRANSFER: 0.0,
    }

    for stream in streams:
        if stream.bucket not in UPCOMING_RECURRING_BUCKETS:
            continue
        if not _is_in_month(stream.predicted_next_date, month_year, month_month):
            continue
        if _stream_already_posted_this_month(stream, current_month_transaction_ids):
            continue

        amount = stream.last_amount or stream.average_amount or 0
        if stream.bucket == INCOME:
            amount = abs(amount)
        totals[stream.bucket] = totals.get(stream.bucket, 0.0) + amount

    return totals


def _upcoming_streams_for_month(
    streams: list[RecurringStream],
    current_month_transaction_ids: set[str],
    *,
    month_year: int,
    month_month: int,
) -> list[RecurringStream]:
    return [
        stream
        for stream in streams
        if stream.bucket in UPCOMING_RECURRING_BUCKETS
        and _is_in_month(stream.predicted_next_date, month_year, month_month)
        and not _stream_already_posted_this_month(stream, current_month_transaction_ids)
    ]


def _stringify(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _dedupe_liabilities(
    liabilities: list[PlaidCreditCardLiability],
) -> list[PlaidCreditCardLiability]:
    deduped: dict[str, PlaidCreditCardLiability] = {}
    for liability in liabilities:
        existing = deduped.get(liability.account_id)
        if existing is None:
            deduped[liability.account_id] = liability
            continue

        existing_balance = existing.current_balance or 0
        candidate_balance = liability.current_balance or 0
        if candidate_balance > existing_balance:
            deduped[liability.account_id] = liability

    return list(deduped.values())


def _fallback_liabilities_from_accounts(accounts: list[dict]) -> list[PlaidCreditCardLiability]:
    today = date.today()
    if today.month == 12:
        due_month = date(today.year + 1, 1, 1)
    else:
        due_month = date(today.year, today.month + 1, 1)

    due_day = min(5, calendar.monthrange(due_month.year, due_month.month)[1])
    due_date = due_month.replace(day=due_day).isoformat()
    liabilities: list[PlaidCreditCardLiability] = []

    for account in accounts:
        if account.get("type") != "credit":
            continue

        balance = float(account.get("balance") or 0)
        if balance <= 0:
            continue

        liabilities.append(
            PlaidCreditCardLiability(
                account_id=account["account_id"],
                item_id=account.get("item_id"),
                institution_id=account.get("institution_id"),
                institution_name=account.get("institution_name"),
                account_name=account.get("name") or account.get("official_name") or "Credit Card",
                current_balance=balance,
                last_statement_balance=balance,
                minimum_payment_amount=round(max(25, balance * 0.02), 2),
                next_payment_due_date=due_date,
            )
        )

    return liabilities
