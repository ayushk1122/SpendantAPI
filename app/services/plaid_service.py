import json

from fastapi import Depends
import plaid
from plaid.api import plaid_api
from plaid.exceptions import ApiException
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.personal_finance_category_version import PersonalFinanceCategoryVersion
from plaid.model.products import Products
from plaid.model.transactions_recurring_get_request import TransactionsRecurringGetRequest
from plaid.model.transactions_recurring_get_request_options import (
    TransactionsRecurringGetRequestOptions,
)
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_sync_request_options import TransactionsSyncRequestOptions

from app.config import Settings, get_settings
from app.schemas.plaid import (
    AccountsResponse,
    BalancesResponse,
    CreateLinkTokenRequest,
    CreateLinkTokenResponse,
    ExchangePublicTokenRequest,
    ExchangePublicTokenResponse,
    PlaidAccount,
    PlaidBalance,
    PlaidInstitutionAccounts,
    LiabilitiesResponse,
    PlaidCreditCardLiability,
    PlaidItemSummary,
    PlaidItemsResponse,
    PlaidTransaction,
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

        access_token = response["access_token"]
        item_id = response["item_id"]
        institution_id = request.institution_id
        institution_name = request.institution_name

        if not institution_id or not institution_name:
            resolved_id, resolved_name = self._resolve_institution_metadata(access_token)
            institution_id = institution_id or resolved_id
            institution_name = institution_name or resolved_name

        item = self.item_store.save_item(
            client_user_id=request.client_user_id,
            access_token=access_token,
            item_id=item_id,
            institution_id=institution_id,
            institution_name=institution_name,
        )

        return ExchangePublicTokenResponse(
            mock=False,
            environment=self.environment,
            access_token=item.access_token,
            item_id=item.item_id,
            institution_id=item.institution_id,
            institution_name=item.institution_name,
            request_id=response.get("request_id"),
        )

    def get_items(self, client_user_id: str) -> PlaidItemsResponse:
        items = self.item_store.get_items(client_user_id)
        summaries: list[PlaidItemSummary] = []

        for item in items:
            account_count = 0
            try:
                accounts_response = self.client.accounts_get(
                    AccountsGetRequest(access_token=item.access_token)
                ).to_dict()
                account_count = len(accounts_response.get("accounts", []))
            except ApiException:
                account_count = 0

            summaries.append(
                PlaidItemSummary(
                    item_id=item.item_id,
                    institution_id=item.institution_id,
                    institution_name=item.institution_name,
                    account_count=account_count,
                )
            )

        return PlaidItemsResponse(items=summaries, mock=False)

    def delete_item(self, client_user_id: str, item_id: str) -> None:
        deleted = self.item_store.delete_item(client_user_id, item_id)
        if not deleted:
            raise PlaidItemNotFoundError(
                f"No Plaid item '{item_id}' is linked for client_user_id '{client_user_id}'."
            )

    def get_accounts(self, client_user_id: str) -> AccountsResponse:
        items = self._get_items(client_user_id)
        all_accounts: list[PlaidAccount] = []
        institutions: list[PlaidInstitutionAccounts] = []
        request_id = None

        for item in items:
            try:
                response = self.client.accounts_get(
                    AccountsGetRequest(access_token=item.access_token)
                ).to_dict()
            except ApiException as exc:
                raise ExternalServiceError(
                    f"Plaid accounts fetch failed: {self._format_plaid_error(exc)}"
                ) from exc

            request_id = response.get("request_id")
            mapped_accounts = [
                self._map_account(account, item)
                for account in response["accounts"]
            ]
            all_accounts.extend(mapped_accounts)
            institutions.append(
                PlaidInstitutionAccounts(
                    item_id=item.item_id,
                    institution_id=item.institution_id,
                    institution_name=item.institution_name,
                    accounts=mapped_accounts,
                )
            )

        return AccountsResponse(
            mock=False,
            accounts=all_accounts,
            institutions=institutions,
            request_id=request_id,
        )

    def get_transactions(self, client_user_id: str) -> TransactionsResponse:
        items = self._get_items(client_user_id)
        total_added = 0
        total_modified = 0
        total_removed = 0
        request_id = None

        for item in items:
            added, modified, removed, next_cursor, item_request_id = self._sync_item_transactions(
                item
            )
            total_added += len(added)
            total_modified += len(modified)
            total_removed += len(removed)
            request_id = item_request_id or request_id

            if next_cursor is not None:
                self.item_store.save_transaction_sync(
                    client_user_id=client_user_id,
                    item_id=item.item_id,
                    added=added,
                    modified=modified,
                    removed=removed,
                    cursor=next_cursor,
                )

        cached_transactions = self.item_store.get_transactions(client_user_id)
        return TransactionsResponse(
            mock=False,
            transactions=[PlaidTransaction(**transaction) for transaction in cached_transactions],
            added_count=total_added,
            modified_count=total_modified,
            removed_count=total_removed,
            request_id=request_id,
        )

    def get_recurring_transactions(self, client_user_id: str) -> dict:
        items = self._get_items(client_user_id)
        combined_outflow_streams: list[dict] = []
        combined_inflow_streams: list[dict] = []

        for item in items:
            try:
                response = self.client.transactions_recurring_get(
                    TransactionsRecurringGetRequest(
                        access_token=item.access_token,
                        options=TransactionsRecurringGetRequestOptions(
                            include_personal_finance_category=True,
                            personal_finance_category_version=PersonalFinanceCategoryVersion("v2"),
                        ),
                    )
                ).to_dict()
            except ApiException as exc:
                raise ExternalServiceError(
                    f"Plaid recurring transactions fetch failed: {self._format_plaid_error(exc)}"
                ) from exc

            combined_outflow_streams.extend(response.get("outflow_streams") or [])
            combined_inflow_streams.extend(response.get("inflow_streams") or [])

        return {
            "outflow_streams": combined_outflow_streams,
            "inflow_streams": combined_inflow_streams,
        }

    def get_liabilities(self, client_user_id: str) -> LiabilitiesResponse:
        items = self._get_items(client_user_id)
        credit_cards: list[PlaidCreditCardLiability] = []
        request_id = None
        account_names: dict[str, str] = {}
        account_balances: dict[str, float | None] = {}

        for item in items:
            try:
                accounts_response = self.client.accounts_get(
                    AccountsGetRequest(access_token=item.access_token)
                ).to_dict()
            except ApiException:
                accounts_response = {"accounts": []}

            for account in accounts_response.get("accounts", []):
                account_id = account["account_id"]
                account_names[account_id] = account.get("name") or account.get("official_name") or "Credit Card"
                balances = account.get("balances") or {}
                account_balances[account_id] = balances.get("current")

            try:
                response = self.client.liabilities_get(
                    LiabilitiesGetRequest(access_token=item.access_token)
                ).to_dict()
            except ApiException as exc:
                error_text = self._format_plaid_error(exc)
                if any(
                    marker in error_text
                    for marker in (
                        "PRODUCT_NOT_READY",
                        "INVALID_PRODUCT",
                        "NO_LIABILITY_ACCOUNTS",
                        "PRODUCTS_NOT_SUPPORTED",
                    )
                ):
                    continue
                raise ExternalServiceError(
                    f"Plaid liabilities fetch failed: {error_text}"
                ) from exc

            request_id = response.get("request_id")
            for liability in response.get("credit", []) or []:
                account_id = liability.get("account_id")
                if not account_id:
                    continue

                credit_cards.append(
                    PlaidCreditCardLiability(
                        account_id=account_id,
                        item_id=item.item_id,
                        institution_id=item.institution_id,
                        institution_name=item.institution_name,
                        account_name=account_names.get(account_id),
                        current_balance=account_balances.get(account_id),
                        last_statement_balance=liability.get("last_statement_balance"),
                        minimum_payment_amount=liability.get("minimum_payment_amount"),
                        next_payment_due_date=self._stringify(
                            liability.get("next_payment_due_date")
                        ),
                        last_statement_issue_date=self._stringify(
                            liability.get("last_statement_issue_date")
                        ),
                        last_payment_amount=liability.get("last_payment_amount"),
                        last_payment_date=self._stringify(liability.get("last_payment_date")),
                        is_overdue=liability.get("is_overdue", False),
                    )
                )

        return LiabilitiesResponse(
            credit_cards=credit_cards,
            mock=False,
            request_id=request_id,
        )

    def get_balances(self, client_user_id: str) -> BalancesResponse:
        items = self._get_items(client_user_id)
        balances: list[PlaidBalance] = []
        request_id = None

        for item in items:
            try:
                response = self.client.accounts_get(
                    AccountsGetRequest(access_token=item.access_token)
                ).to_dict()
            except ApiException as exc:
                raise ExternalServiceError(
                    f"Plaid balances fetch failed: {self._format_plaid_error(exc)}"
                ) from exc

            request_id = response.get("request_id")
            balances.extend(
                self._map_balance(account, item)
                for account in response["accounts"]
            )

        return BalancesResponse(mock=False, balances=balances, request_id=request_id)

    def _sync_item_transactions(
        self,
        item: PlaidItem,
    ) -> tuple[list[dict], list[dict], list[dict], str | None, str | None]:
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
                "options": TransactionsSyncRequestOptions(
                    include_personal_finance_category=True,
                    personal_finance_category_version=PersonalFinanceCategoryVersion("v2"),
                ),
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

            added.extend(
                self._map_transaction(transaction, item.item_id)
                for transaction in response["added"]
            )
            modified.extend(
                self._map_transaction(transaction, item.item_id)
                for transaction in response["modified"]
            )
            removed.extend(response["removed"])
            modified_count += len(response["modified"])
            removed_count += len(response["removed"])
            next_cursor = response["next_cursor"]
            request_id = response.get("request_id")
            has_more = response["has_more"]

        return added, modified, removed, next_cursor, request_id

    def _resolve_institution_metadata(
        self,
        access_token: str,
    ) -> tuple[str | None, str | None]:
        try:
            item_response = self.client.item_get(
                ItemGetRequest(access_token=access_token)
            ).to_dict()
        except ApiException:
            return None, None

        institution_id = item_response.get("item", {}).get("institution_id")
        if not institution_id:
            return None, None

        try:
            institution_response = self.client.institutions_get_by_id(
                InstitutionsGetByIdRequest(
                    institution_id=institution_id,
                    country_codes=[CountryCode("US")],
                )
            ).to_dict()
        except ApiException:
            return institution_id, None

        institution_name = institution_response.get("institution", {}).get("name")
        return institution_id, institution_name

    def _get_items(self, client_user_id: str) -> list[PlaidItem]:
        items = self.item_store.get_items(client_user_id)
        if not items:
            raise PlaidItemNotFoundError(
                f"No Plaid items are linked for client_user_id '{client_user_id}'."
            )
        return items

    def _map_account(self, account: dict, item: PlaidItem) -> PlaidAccount:
        balances = account["balances"]
        return PlaidAccount(
            account_id=account["account_id"],
            item_id=item.item_id,
            institution_id=item.institution_id,
            institution_name=item.institution_name,
            name=account["name"],
            official_name=account.get("official_name"),
            type=self._stringify(account["type"]) or "unknown",
            subtype=self._stringify(account.get("subtype")),
            balance=balances.get("current"),
            available_balance=balances.get("available"),
            iso_currency_code=balances.get("iso_currency_code"),
        )

    def _map_balance(self, account: dict, item: PlaidItem) -> PlaidBalance:
        balances = account["balances"]
        return PlaidBalance(
            account_id=account["account_id"],
            item_id=item.item_id,
            institution_id=item.institution_id,
            institution_name=item.institution_name,
            available=balances.get("available"),
            current=balances.get("current"),
            iso_currency_code=balances.get("iso_currency_code"),
        )

    def _map_transaction(self, transaction: dict, item_id: str) -> dict:
        personal_finance_category = transaction.get("personal_finance_category") or {}
        return {
            "transaction_id": transaction["transaction_id"],
            "item_id": item_id,
            "account_id": transaction["account_id"],
            "name": transaction["name"],
            "amount": transaction["amount"],
            "date": str(transaction["date"]),
            "plaid_primary_category": personal_finance_category.get("primary"),
            "plaid_detailed_category": personal_finance_category.get("detailed"),
            "plaid_category_confidence": personal_finance_category.get("confidence_level"),
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
