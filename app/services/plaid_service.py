from fastapi import Depends

from app.config import Settings, get_settings


class PlaidService:
    def __init__(self, settings: Settings) -> None:
        self.client_id = settings.plaid_client_id
        self.secret = settings.plaid_secret
        self.environment = settings.plaid_env

    def create_link_token(self) -> dict[str, object]:
        return {
            "mock": True,
            "environment": self.environment,
            "link_token": "link-sandbox-mock-token",
        }

    def exchange_public_token(self) -> dict[str, object]:
        return {
            "mock": True,
            "environment": self.environment,
            "access_token": "access-sandbox-mock-token",
            "item_id": "mock-item-id",
        }

    def get_accounts(self) -> dict[str, object]:
        return {
            "mock": True,
            "accounts": [
                {
                    "account_id": "mock-checking",
                    "name": "Spendant Checking",
                    "type": "depository",
                    "subtype": "checking",
                    "balance": 2450.75,
                }
            ],
        }

    def get_transactions(self) -> dict[str, object]:
        return {
            "mock": True,
            "transactions": [
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
        }

    def get_balances(self) -> dict[str, object]:
        return {
            "mock": True,
            "balances": [
                {
                    "account_id": "mock-checking",
                    "available": 2450.75,
                    "current": 2500.75,
                    "iso_currency_code": "USD",
                }
            ],
        }


def get_plaid_service(settings: Settings = Depends(get_settings)) -> PlaidService:
    return PlaidService(settings)

