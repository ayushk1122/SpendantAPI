from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PlaidCountryCode = Literal["US"]
PlaidProduct = Literal["transactions", "liabilities"]


class CreateLinkTokenRequest(BaseModel):
    client_user_id: str = Field(default="spendant-local-user")
    client_name: str = Field(default="Spendant")
    language: str = Field(default="en")
    products: list[PlaidProduct] = Field(
        default_factory=lambda: ["transactions", "liabilities"]
    )
    country_codes: list[PlaidCountryCode] = Field(default_factory=lambda: ["US"])


class CreateLinkTokenResponse(BaseModel):
    link_token: str
    expiration: datetime | None = None
    request_id: str | None = None
    environment: str
    mock: bool = False


class ExchangePublicTokenRequest(BaseModel):
    public_token: str
    client_user_id: str = Field(default="spendant-local-user")
    institution_id: str | None = None
    institution_name: str | None = None


class ExchangePublicTokenResponse(BaseModel):
    access_token: str
    item_id: str
    institution_id: str | None = None
    institution_name: str | None = None
    environment: str
    mock: bool = True
    request_id: str | None = None


class PlaidItemSummary(BaseModel):
    item_id: str
    institution_id: str | None = None
    institution_name: str | None = None
    account_count: int = 0


class PlaidItemsResponse(BaseModel):
    items: list[PlaidItemSummary]
    mock: bool = False


class PlaidAccount(BaseModel):
    account_id: str
    item_id: str | None = None
    institution_id: str | None = None
    institution_name: str | None = None
    name: str
    official_name: str | None = None
    type: str
    subtype: str | None = None
    balance: float | None = None
    available_balance: float | None = None
    iso_currency_code: str | None = None


class PlaidInstitutionAccounts(BaseModel):
    item_id: str
    institution_id: str | None = None
    institution_name: str | None = None
    accounts: list[PlaidAccount]


class AccountsResponse(BaseModel):
    accounts: list[PlaidAccount]
    institutions: list[PlaidInstitutionAccounts] = []
    mock: bool = True
    request_id: str | None = None


class PlaidTransaction(BaseModel):
    transaction_id: str
    item_id: str | None = None
    account_id: str
    name: str
    amount: float
    date: str
    plaid_primary_category: str | None = None
    plaid_detailed_category: str | None = None
    plaid_category_confidence: str | None = None
    category: list[str] | None = None
    merchant_name: str | None = None
    pending: bool = False
    iso_currency_code: str | None = None


class TransactionsResponse(BaseModel):
    transactions: list[PlaidTransaction]
    mock: bool = True
    added_count: int = 0
    modified_count: int = 0
    removed_count: int = 0
    next_cursor: str | None = None
    request_id: str | None = None


class PlaidBalance(BaseModel):
    account_id: str
    item_id: str | None = None
    institution_id: str | None = None
    institution_name: str | None = None
    available: float | None = None
    current: float | None = None
    iso_currency_code: str | None = None


class BalancesResponse(BaseModel):
    balances: list[PlaidBalance]
    mock: bool = True
    request_id: str | None = None


class PlaidCreditCardLiability(BaseModel):
    account_id: str
    item_id: str | None = None
    institution_id: str | None = None
    institution_name: str | None = None
    account_name: str | None = None
    current_balance: float | None = None
    last_statement_balance: float | None = None
    minimum_payment_amount: float | None = None
    next_payment_due_date: str | None = None
    last_statement_issue_date: str | None = None
    last_payment_amount: float | None = None
    last_payment_date: str | None = None
    is_overdue: bool = False


class LiabilitiesResponse(BaseModel):
    credit_cards: list[PlaidCreditCardLiability]
    mock: bool = False
    request_id: str | None = None
