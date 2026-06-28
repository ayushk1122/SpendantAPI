import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Spendant Plaid endpoints.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--client-user-id", default="spendant-smoke-user")
    parser.add_argument(
        "--create-sandbox-token",
        action="store_true",
        help="Create a Plaid sandbox public token and test the full exchange/read flow.",
    )
    parser.add_argument(
        "--link-second-institution",
        action="store_true",
        help="After the first sandbox link, link a second institution to verify multi-bank support.",
    )
    parser.add_argument("--public-token", help="Use an existing Plaid public token.")
    parser.add_argument("--institution-id", default="ins_109508")
    parser.add_argument(
        "--second-institution-id",
        default="ins_109509",
        help="Sandbox institution to link when --link-second-institution is set.",
    )
    args = parser.parse_args()

    public_token = args.public_token
    if args.create_sandbox_token:
        public_token = create_sandbox_public_token(args.institution_id)
        print("created sandbox public token")

    check("health", request_json("GET", f"{args.base_url}/health"))
    check("health ready", request_json("GET", f"{args.base_url}/health/ready"))
    link_token = request_json(
        "POST",
        f"{args.base_url}/api/plaid/create-link-token",
        {"client_user_id": args.client_user_id},
    )
    check("create link token", link_token, required=["link_token"])

    if not public_token:
        print("skipping exchange/accounts/balances/transactions; no public token provided")
        print("rerun with --create-sandbox-token for the full Plaid sandbox smoke test")
        return 0

    exchange = request_json(
        "POST",
        f"{args.base_url}/api/plaid/exchange-public-token",
        {
            "public_token": public_token,
            "client_user_id": args.client_user_id,
        },
    )
    check("exchange public token", exchange, required=["item_id"])
    if "access_token" in exchange:
        raise RuntimeError("exchange response must not include access_token")

    if args.link_second_institution:
        second_token = create_sandbox_public_token(args.second_institution_id)
        print("created second sandbox public token")
        second_exchange = request_json(
            "POST",
            f"{args.base_url}/api/plaid/exchange-public-token",
            {
                "public_token": second_token,
                "client_user_id": args.client_user_id,
            },
        )
        check(
            "exchange second public token",
            second_exchange,
            required=["item_id"],
        )
        if "access_token" in second_exchange:
            raise RuntimeError("exchange response must not include access_token")
        if second_exchange["item_id"] == exchange["item_id"]:
            raise RuntimeError("second institution exchange returned the same item_id")

    query = urlencode({"client_user_id": args.client_user_id})
    items = request_json("GET", f"{args.base_url}/api/plaid/items?{query}")
    check("items", items, required=["items"])
    if args.link_second_institution and len(items["items"]) < 2:
        raise RuntimeError(
            f"expected at least 2 linked items, got {len(items['items'])}"
        )

    accounts = request_json("GET", f"{args.base_url}/api/plaid/accounts?{query}")
    check("accounts", accounts, required=["accounts", "institutions"])
    if args.link_second_institution and len(accounts["institutions"]) < 2:
        raise RuntimeError(
            "expected accounts grouped across at least 2 institutions"
        )

    balances = request_json("GET", f"{args.base_url}/api/plaid/balances?{query}")
    check("balances", balances, required=["balances"])

    transactions = request_json("GET", f"{args.base_url}/api/plaid/transactions?{query}")
    check("transactions", transactions, required=["transactions"])

    print("plaid endpoint smoke test passed")
    return 0


def create_sandbox_public_token(institution_id: str) -> str:
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


def check(label: str, response: dict, required: list[str] | None = None) -> None:
    required = required or []
    missing = [field for field in required if field not in response]
    if missing:
        raise RuntimeError(f"{label} response missing fields: {', '.join(missing)}")

    print(f"{label}: ok")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
