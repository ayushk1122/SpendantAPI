from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PlaidCountryCode = Literal["US"]
PlaidProduct = Literal["transactions"]


class CreateLinkTokenRequest(BaseModel):
    client_user_id: str = Field(default="spendant-local-user")
    client_name: str = Field(default="Spendant")
    language: str = Field(default="en")
    products: list[PlaidProduct] = Field(default_factory=lambda: ["transactions"])
    country_codes: list[PlaidCountryCode] = Field(default_factory=lambda: ["US"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_user_id": "local-user",
                "client_name": "Spendant",
                "language": "en",
                "products": ["transactions"],
                "country_codes": ["US"],
            }
        }
    }


class CreateLinkTokenResponse(BaseModel):
    link_token: str
    expiration: datetime | None = None
    request_id: str | None = None
    environment: str
    mock: bool = False


class ExchangePublicTokenRequest(BaseModel):
    public_token: str


class ExchangePublicTokenResponse(BaseModel):
    access_token: str
    item_id: str
    environment: str
    mock: bool = True


class PlaidAccount(BaseModel):
    account_id: str
    name: str
    type: str
    subtype: str
    balance: float


class AccountsResponse(BaseModel):
    accounts: list[PlaidAccount]
    mock: bool = True


class PlaidTransaction(BaseModel):
    transaction_id: str
    name: str
    amount: float
    date: str
    category: list[str]


class TransactionsResponse(BaseModel):
    transactions: list[PlaidTransaction]
    mock: bool = True


class PlaidBalance(BaseModel):
    account_id: str
    available: float
    current: float
    iso_currency_code: str


class BalancesResponse(BaseModel):
    balances: list[PlaidBalance]
    mock: bool = True
