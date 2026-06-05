import logging
from datetime import date

from fastapi import Depends

from app.config import Settings, get_settings
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    NormalizedTransaction,
    RecurringStream,
)
from app.services.plaid_service import ExternalServiceError, PlaidService
from app.services.transaction_classifier import (
    EXPENSES,
    HOUSING,
    INCOME,
    SUBSCRIPTIONS,
    TRANSFER,
    classify_transaction,
)

logger = logging.getLogger(__name__)

PROTECTED_BALANCE_DEFAULT = 30.0


class DashboardService:
    def __init__(self, plaid_service: PlaidService) -> None:
        self.plaid_service = plaid_service

    def get_dashboard_summary(self, client_user_id: str) -> DashboardSummaryResponse:
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
        current_month_transactions = [
            transaction
            for transaction in transactions
            if _is_current_month(transaction.get("date"))
        ]

        normalized_transactions = [
            self._normalize_transaction(
                transaction,
                recurring_bucket_by_transaction_id.get(transaction["transaction_id"]),
            )
            for transaction in current_month_transactions
        ]
        current_month_transaction_ids = {
            transaction["transaction_id"]
            for transaction in current_month_transactions
        }
        upcoming_recurring_totals = _upcoming_recurring_totals(
            recurring_streams,
            current_month_transaction_ids,
        )

        income_total = round(
            sum(
                abs(transaction.amount)
                for transaction in normalized_transactions
                if transaction.bucket == INCOME
            )
            + upcoming_recurring_totals[INCOME],
            2,
        )
        housing_total = round(
            sum(
                transaction.amount
                for transaction in normalized_transactions
                if transaction.bucket == HOUSING
            )
            + upcoming_recurring_totals[HOUSING],
            2,
        )
        expenses_total = round(
            sum(
                transaction.amount
                for transaction in normalized_transactions
                if transaction.bucket == EXPENSES
            )
            + upcoming_recurring_totals[EXPENSES],
            2,
        )
        subscriptions_total = round(
            sum(
                transaction.amount
                for transaction in normalized_transactions
                if transaction.bucket == SUBSCRIPTIONS
            )
            + upcoming_recurring_totals[SUBSCRIPTIONS],
            2,
        )
        transfer_total = round(
            sum(
                transaction.amount
                for transaction in normalized_transactions
                if transaction.bucket == TRANSFER
            )
            + upcoming_recurring_totals[TRANSFER],
            2,
        )

        checking_balance = _find_checking_balance(
            [account.model_dump() for account in accounts_response.accounts]
        )
        protected_balance = PROTECTED_BALANCE_DEFAULT
        projected_month_end_balance = round(
            checking_balance
            + income_total
            - housing_total
            - expenses_total
            - subscriptions_total,
            2,
        )
        safe_to_move_amount = round(
            max(0, projected_month_end_balance - protected_balance),
            2,
        )

        logger.info(
            "dashboard summary client_user_id=%s fetched_transactions=%s current_month_transactions=%s",
            client_user_id,
            len(transactions),
            len(current_month_transactions),
        )
        logger.info(
            "dashboard recurring client_user_id=%s active_streams=%s upcoming_totals=%s",
            client_user_id,
            len(recurring_streams),
            upcoming_recurring_totals,
        )
        logger.info(
            "dashboard totals client_user_id=%s income=%s housing=%s expenses=%s subscriptions=%s transfers=%s safe_to_move=%s",
            client_user_id,
            income_total,
            housing_total,
            expenses_total,
            subscriptions_total,
            transfer_total,
            safe_to_move_amount,
        )

        return DashboardSummaryResponse(
            checking_balance=checking_balance,
            income_total=income_total,
            housing_total=housing_total,
            expenses_total=expenses_total,
            subscriptions_total=subscriptions_total,
            transfer_total=transfer_total,
            protected_balance=protected_balance,
            projected_month_end_balance=projected_month_end_balance,
            safe_to_move_amount=safe_to_move_amount,
            transactions=normalized_transactions,
            recurring_streams=recurring_streams,
        )

    def _normalize_transaction(
        self,
        transaction: dict,
        recurring_bucket: str | None = None,
    ) -> NormalizedTransaction:
        return NormalizedTransaction(
            transaction_id=transaction["transaction_id"],
            account_id=transaction.get("account_id"),
            name=transaction["name"],
            merchant_name=transaction.get("merchant_name"),
            amount=transaction["amount"],
            date=transaction["date"],
            bucket=recurring_bucket or classify_transaction(transaction),
            pending=transaction.get("pending", False),
            plaid_primary_category=transaction.get("plaid_primary_category"),
            plaid_detailed_category=transaction.get("plaid_detailed_category"),
            plaid_category_confidence=transaction.get("plaid_category_confidence"),
        )

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

        outflow_streams = response.get("outflow_streams") or []
        return [
            _normalize_recurring_stream(stream)
            for stream in outflow_streams
            if stream.get("is_active", False)
        ]


def get_dashboard_service(settings: Settings = Depends(get_settings)) -> DashboardService:
    return DashboardService(PlaidService(settings))


def _find_checking_balance(accounts: list[dict]) -> float:
    for account in accounts:
        if account.get("type") == "depository" and account.get("subtype") == "checking":
            return float(
                account.get("balance")
                or account.get("current")
                or account.get("available_balance")
                or 0
            )

    return 0.0


def _is_current_month(value: str | None) -> bool:
    if not value:
        return False

    try:
        transaction_date = date.fromisoformat(value)
    except ValueError:
        return False

    today = date.today()
    return transaction_date.year == today.year and transaction_date.month == today.month


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
    if bucket == EXPENSES:
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
        for transaction_id in stream.transaction_ids:
            bucket_by_transaction_id[transaction_id] = stream.bucket
    return bucket_by_transaction_id


def _upcoming_recurring_totals(
    streams: list[RecurringStream],
    current_month_transaction_ids: set[str],
) -> dict[str, float]:
    totals = {
        INCOME: 0.0,
        HOUSING: 0.0,
        EXPENSES: 0.0,
        SUBSCRIPTIONS: 0.0,
        TRANSFER: 0.0,
    }

    for stream in streams:
        if not _is_current_month(stream.predicted_next_date):
            continue
        if any(
            transaction_id in current_month_transaction_ids
            for transaction_id in stream.transaction_ids
        ):
            continue

        amount = stream.last_amount or stream.average_amount or 0
        totals[stream.bucket] = totals.get(stream.bucket, 0.0) + amount

    return totals


def _stringify(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)
