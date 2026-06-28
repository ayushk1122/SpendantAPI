from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.plaid import (
    AccountsResponse,
    LiabilitiesResponse,
    PlaidAccount,
    PlaidTransaction,
    TransactionsResponse,
)
from app.services.plaid_service import ExternalServiceError


@dataclass
class FakePlaidService:
    accounts: list[PlaidAccount] = field(default_factory=list)
    transactions: list[PlaidTransaction] = field(default_factory=list)
    recurring_response: dict | None = field(default_factory=dict)
    liabilities_response: object | None = None
    liabilities_error: Exception | None = None

    def get_accounts(self, client_user_id: str) -> AccountsResponse:
        return AccountsResponse(accounts=self.accounts, institutions=[])

    def get_transactions(self, client_user_id: str) -> TransactionsResponse:
        return TransactionsResponse(transactions=self.transactions)

    def get_recurring_transactions(self, client_user_id: str) -> dict:
        return self.recurring_response or {"inflow_streams": [], "outflow_streams": []}

    def get_liabilities(self, client_user_id: str) -> LiabilitiesResponse:
        if self.liabilities_error:
            raise self.liabilities_error
        if self.liabilities_response is None:
            return LiabilitiesResponse(credit_cards=[])
        return self.liabilities_response


def checking_account(balance: float = 5000.0) -> PlaidAccount:
    return PlaidAccount(
        account_id="checking-1",
        item_id="item-1",
        institution_id="ins_1",
        institution_name="Test Bank",
        name="Checking",
        official_name="Checking",
        type="depository",
        subtype="checking",
        balance=balance,
        available_balance=balance,
    )


def plaid_transaction(
    *,
    transaction_id: str,
    amount: float,
    date: str,
    name: str,
    primary: str | None = None,
    detailed: str | None = None,
    merchant_name: str | None = None,
) -> PlaidTransaction:
    return PlaidTransaction(
        transaction_id=transaction_id,
        account_id="checking-1",
        item_id="item-1",
        name=name,
        merchant_name=merchant_name or name,
        amount=amount,
        date=date,
        pending=False,
        category=[],
        plaid_primary_category=primary,
        plaid_detailed_category=detailed,
        plaid_category_confidence="HIGH",
    )
