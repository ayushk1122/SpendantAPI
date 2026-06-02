import json

from fastapi import Depends
import plaid
from plaid.api import plaid_api
from plaid.exceptions import ApiException
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest

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
from app.services.plaid_item_store import PlaidItem, PlaidItemStore


class ExternalServiceError(RuntimeError):
    pass


class PlaidItemNotFoundError(RuntimeError):
    pass


class PlaidService:
    def __init__(self, settings: Settings) -> None:
        self.client_id = settings.plaid_client_id
        self.secret = settings.plaid_secret
        self.environment = settings.plaid_env
        self.item_store = PlaidItemStore(settings.plaid_storage_path)
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
        request: ExchangePublicTokenRequest,
    ) -> ExchangePublicTokenResponse:
        plaid_request = ItemPublicTokenExchangeRequest(public_token=request.public_token)

        try:
            response = self.client.item_public_token_exchange(plaid_request).to_dict()
        except ApiException as exc:
            raise ExternalServiceError(
                f"Plaid public token exchange failed: {self._format_plaid_error(exc)}"
            ) from exc

        item = self.item_store.save_item(
            client_user_id=request.client_user_id,
            access_token=response["access_token"],
            item_id=response["item_id"],
        )

        return ExchangePublicTokenResponse(
            mock=False,
            environment=self.environment,
            access_token=item.access_token,
            item_id=item.item_id,
            request_id=response.get("request_id"),
        )

    def get_accounts(self, client_user_id: str) -> AccountsResponse:
        item = self._get_item(client_user_id)

        try:
            response = self.client.accounts_get(
                AccountsGetRequest(access_token=item.access_token)
            ).to_dict()
        except ApiException as exc:
            raise ExternalServiceError(
                f"Plaid accounts fetch failed: {self._format_plaid_error(exc)}"
            ) from exc

        return AccountsResponse(
            mock=False,
            accounts=[self._map_account(account) for account in response["accounts"]],
            request_id=response.get("request_id"),
        )

    def get_transactions(self, client_user_id: str) -> TransactionsResponse:
        item = self._get_item(client_user_id)
        added: list[dict] = []
        modified: list[dict] = []
        removed: list[dict] = []
        modified_count = 0
        removed_count = 0
        next_cursor = item.transactions_cursor
        request_id = None
        has_more = True

        while has_more:
            request_kwargs = {
                "access_token": item.access_token,
                "count": 500,
            }
            if next_cursor:
                request_kwargs["cursor"] = next_cursor

            try:
                response = self.client.transactions_sync(
                    TransactionsSyncRequest(**request_kwargs)
                ).to_dict()
            except ApiException as exc:
                raise ExternalServiceError(
                    f"Plaid transaction sync failed: {self._format_plaid_error(exc)}"
                ) from exc

            added.extend(self._map_transaction(transaction) for transaction in response["added"])
            modified.extend(
                self._map_transaction(transaction) for transaction in response["modified"]
            )
            removed.extend(response["removed"])
            modified_count += len(response["modified"])
            removed_count += len(response["removed"])
            next_cursor = response["next_cursor"]
            request_id = response.get("request_id")
            has_more = response["has_more"]

        if next_cursor:
            self.item_store.save_transaction_sync(
                client_user_id=client_user_id,
                added=added,
                modified=modified,
                removed=removed,
                cursor=next_cursor,
            )

        return TransactionsResponse(
            mock=False,
            transactions=self.item_store.get_transactions(client_user_id),
            added_count=len(added),
            modified_count=modified_count,
            removed_count=removed_count,
            next_cursor=next_cursor,
            request_id=request_id,
        )

    def get_balances(self, client_user_id: str) -> BalancesResponse:
        item = self._get_item(client_user_id)

        try:
            response = self.client.accounts_get(
                AccountsGetRequest(access_token=item.access_token)
            ).to_dict()
        except ApiException as exc:
            raise ExternalServiceError(
                f"Plaid balances fetch failed: {self._format_plaid_error(exc)}"
            ) from exc

        return BalancesResponse(
            mock=False,
            balances=[
                self._map_balance(account)
                for account in response["accounts"]
            ],
            request_id=response.get("request_id"),
        )

    def _get_item(self, client_user_id: str) -> PlaidItem:
        item = self.item_store.get_item(client_user_id)
        if item is None:
            raise PlaidItemNotFoundError(
                f"No Plaid item is linked for client_user_id '{client_user_id}'."
            )
        return item

    def _map_account(self, account: dict) -> dict:
        balances = account["balances"]
        return {
            "account_id": account["account_id"],
            "name": account["name"],
            "type": self._stringify(account["type"]),
            "subtype": self._stringify(account.get("subtype")),
            "balance": balances.get("current"),
            "available_balance": balances.get("available"),
            "iso_currency_code": balances.get("iso_currency_code"),
        }

    def _map_balance(self, account: dict) -> dict:
        balances = account["balances"]
        return {
            "account_id": account["account_id"],
            "available": balances.get("available"),
            "current": balances.get("current"),
            "iso_currency_code": balances.get("iso_currency_code"),
        }

    def _map_transaction(self, transaction: dict) -> dict:
        return {
            "transaction_id": transaction["transaction_id"],
            "account_id": transaction["account_id"],
            "name": transaction["name"],
            "amount": transaction["amount"],
            "date": str(transaction["date"]),
            "category": transaction.get("category"),
            "merchant_name": transaction.get("merchant_name"),
            "pending": transaction.get("pending", False),
            "iso_currency_code": transaction.get("iso_currency_code"),
        }

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

    def _stringify(self, value: object | None) -> str | None:
        if value is None:
            return None
        return str(value)


def get_plaid_service(settings: Settings = Depends(get_settings)) -> PlaidService:
    return PlaidService(settings)
