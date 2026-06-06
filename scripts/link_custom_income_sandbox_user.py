import argparse
import calendar
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.sandbox_public_token_create_request_options import (
    SandboxPublicTokenCreateRequestOptions,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


DEFAULT_CLIENT_USER_ID = "spendant-local-user"
DEFAULT_INSTITUTION_ID = "ins_109508"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Link a custom Plaid sandbox Item with current-month income."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--client-user-id", default=DEFAULT_CLIENT_USER_ID)
    parser.add_argument("--institution-id", default=DEFAULT_INSTITUTION_ID)
    parser.add_argument(
        "--checking-balance",
        type=float,
        default=6200,
        help="Starting balance for the custom checking account.",
    )
    parser.add_argument(
        "--monthly-payroll",
        type=float,
        default=3500,
        help="Expected monthly payroll amount.",
    )
    args = parser.parse_args()

    config = build_custom_user_config(
        checking_balance=args.checking_balance,
        monthly_payroll=args.monthly_payroll,
    )
    public_token = create_custom_user_public_token(args.institution_id, config)
    print("created custom sandbox public token")

    exchange = request_json(
        "POST",
        f"{args.base_url}/api/plaid/exchange-public-token",
        {
            "public_token": public_token,
            "client_user_id": args.client_user_id,
            "institution_id": args.institution_id,
            "institution_name": "First Platypus Bank - Custom Income",
        },
    )

    print(f"linked item: {exchange['item_id']}")
    print(f"client user id: {args.client_user_id}")
    print("run scripts/smoke_dashboard.py to verify the dashboard totals")
    return 0


def build_custom_user_config(
    *,
    checking_balance: float,
    monthly_payroll: float,
) -> dict:
    today = date.today()
    first_of_month = today.replace(day=1)
    payroll_day = min(15, calendar.monthrange(today.year, today.month)[1])

    transactions = [
        income_transaction(
            posted_on=max(first_of_month, today - timedelta(days=2)),
            amount=750,
            description="FREELANCE PAYMENT",
        ),
        expense_transaction(
            posted_on=first_of_month,
            amount=1850,
            description="RENT PAYMENT",
        ),
        expense_transaction(
            posted_on=min(first_of_month + timedelta(days=2), today),
            amount=126.42,
            description="WHOLE FOODS MARKET",
        ),
        expense_transaction(
            posted_on=min(first_of_month + timedelta(days=4), today),
            amount=18.99,
            description="NETFLIX.COM",
        ),
    ]

    card_payment_day = min(5, calendar.monthrange(today.year, today.month)[1])
    statement_day = min(28, calendar.monthrange(today.year, today.month)[1])

    return {
        "seed": f"spendant-income-{today.isoformat()}",
        "override_accounts": [
            {
                "type": "depository",
                "subtype": "checking",
                "starting_balance": checking_balance,
                "inflow_model": {
                    "type": "monthly-income",
                    "income_amount": monthly_payroll,
                    "payment_day_of_month": payroll_day,
                    "transaction_name": "ACME PAYROLL DIRECT DEP",
                },
                "identity": {
                    "names": ["Spendant Sandbox User"],
                    "emails": [
                        {
                            "primary": True,
                            "type": "primary",
                            "data": "sandbox-income@spendant.test",
                        }
                    ],
                    "phone_numbers": [],
                    "addresses": [],
                },
                "transactions": transactions,
            },
            {
                "type": "credit",
                "subtype": "credit card",
                "starting_balance": 2400,
                "inflow_model": {
                    "type": "monthly-balance-payment",
                    "payment_day_of_month": card_payment_day,
                    "statement_day_of_month": statement_day,
                    "transaction_name": "CHASE CARD PAYMENT",
                },
                "liability": {
                    "type": "credit",
                    "purchase_apr": 18.9,
                    "last_payment_amount": 500,
                    "minimum_payment_amount": 75,
                    "last_statement_balance": 2100,
                },
            },
        ],
    }


def income_transaction(*, posted_on: date, amount: float, description: str) -> dict:
    return transaction(
        posted_on=posted_on,
        amount=-abs(amount),
        description=description,
    )


def expense_transaction(*, posted_on: date, amount: float, description: str) -> dict:
    return transaction(
        posted_on=posted_on,
        amount=abs(amount),
        description=description,
    )


def transaction(*, posted_on: date, amount: float, description: str) -> dict:
    return {
        "date_transacted": posted_on.isoformat(),
        "date_posted": posted_on.isoformat(),
        "currency": "USD",
        "amount": round(amount, 2),
        "description": description,
    }


def create_custom_user_public_token(institution_id: str, config: dict) -> str:
    settings = get_settings()
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            "clientId": settings.plaid_client_id,
            "secret": settings.plaid_secret,
        },
    )
    client = plaid_api.PlaidApi(plaid.ApiClient(configuration))
    response = client.sandbox_public_token_create(
        SandboxPublicTokenCreateRequest(
            institution_id=institution_id,
            initial_products=[Products("transactions"), Products("liabilities")],
            options=SandboxPublicTokenCreateRequestOptions(
                override_username="user_custom",
                override_password=json.dumps(config),
            ),
        )
    ).to_dict()
    return response["public_token"]


def request_json(method: str, url: str, body: dict | None = None) -> dict:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"custom sandbox user link failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
