import json

from fastapi import Depends
import plaid
from plaid.api import plaid_api
from plaid.exceptions import ApiException
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products

from app.config import Settings, get_settings
from app.schemas.plaid import (
    AccountsResponse,
    BalancesResponse,
    CreateLinkTokenRequest,
    CreateLinkTokenResponse,
    ExchangePublicTokenRequest,
    ExchangePublicTokenResponse,
    TransactionsResponse,
)


class ExternalServiceError(RuntimeError):
    pass


class PlaidService:
    def __init__(self, settings: Settings) -> None:
        self.client_id = settings.plaid_client_id
        self.secret = settings.plaid_secret
        self.environment = settings.plaid_env
        self.client = self._build_client()

    def create_link_token(self, request: CreateLinkTokenRequest) -> CreateLinkTokenResponse:
        plaid_request = LinkTokenCreateRequest(
            client_name=request.client_name,
            language=request.language,
            country_codes=[CountryCode(code) for code in request.country_codes],
            user=LinkTokenCreateRequestUser(client_user_id=request.client_user_id),
            products=[Products(product) for product in request.products],
        )

        try:
            response = self.client.link_token_create(plaid_request).to_dict()
        except ApiException as exc:
            raise ExternalServiceError(
                f"Plaid link token creation failed: {self._format_plaid_error(exc)}"
            ) from exc

        return CreateLinkTokenResponse(
            link_token=response["link_token"],
            expiration=response.get("expiration"),
            request_id=response.get("request_id"),
            environment=self.environment,
            mock=False,
        )

    def exchange_public_token(
        self,
        request: ExchangePublicTokenRequest | None,
    ) -> ExchangePublicTokenResponse:
        return ExchangePublicTokenResponse(
            mock=True,
            environment=self.environment,
            access_token="access-sandbox-mock-token",
            item_id="mock-item-id",
        )

    def get_accounts(self) -> AccountsResponse:
        return AccountsResponse(
            mock=True,
            accounts=[
                {
                    "account_id": "mock-checking",
                    "name": "Spendant Checking",
                    "type": "depository",
                    "subtype": "checking",
                    "balance": 2450.75,
                }
            ],
        )

    def get_transactions(self) -> TransactionsResponse:
        return TransactionsResponse(
            mock=True,
            transactions=[
                {
                    "transaction_id": "mock-transaction-1",
                    "name": "Payroll",
                    "amount": -3200.00,
                    "date": "2026-05-01",
                    "category": ["Income"],
                },
                {
                    "transaction_id": "mock-transaction-2",
                    "name": "Rent",
                    "amount": 1800.00,
                    "date": "2026-05-03",
                    "category": ["Rent"],
                },
            ],
        )

    def get_balances(self) -> BalancesResponse:
        return BalancesResponse(
            mock=True,
            balances=[
                {
                    "account_id": "mock-checking",
                    "available": 2450.75,
                    "current": 2500.75,
                    "iso_currency_code": "USD",
                }
            ],
        )

    def _build_client(self) -> plaid_api.PlaidApi:
        configuration = plaid.Configuration(
            host=self._plaid_host(),
            api_key={
                "clientId": self.client_id,
                "secret": self.secret,
            },
        )
        api_client = plaid.ApiClient(configuration)
        return plaid_api.PlaidApi(api_client)

    def _plaid_host(self) -> str:
        if self.environment == "production":
            return plaid.Environment.Production

        # plaid-python 39.x exposes sandbox and production hosts. Keep accepting
        # "development" in config, but route local development traffic to sandbox.
        return plaid.Environment.Sandbox

    def _format_plaid_error(self, exc: ApiException) -> str:
        if not exc.body:
            return exc.reason

        try:
            error_body = json.loads(exc.body)
        except json.JSONDecodeError:
            return exc.reason

        error_code = error_body.get("error_code")
        error_message = error_body.get("error_message")
        if error_code and error_message:
            return f"{error_code}: {error_message}"
        return exc.reason


def get_plaid_service(settings: Settings = Depends(get_settings)) -> PlaidService:
    return PlaidService(settings)
