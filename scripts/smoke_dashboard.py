import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Spendant dashboard summary.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--client-user-id", default="spendant-local-user")
    args = parser.parse_args()

    query = urlencode({"client_user_id": args.client_user_id})
    summary = request_json("GET", f"{args.base_url}/api/dashboard/summary?{query}")

    print(f"checking balance: {summary['checking_balance']}")
    print(f"income total: {summary['income_total']}")
    print(f"housing total: {summary['housing_total']}")
    print(f"expenses total: {summary['expenses_total']}")
    print(f"subscriptions total: {summary['subscriptions_total']}")
    print(f"safe to move amount: {summary['safe_to_move_amount']}")
    print(f"recurring streams: {len(summary.get('recurring_streams', []))}")
    print("first 5 classified transactions:")

    for transaction in summary["transactions"][:5]:
        print(
            "- {date} {name}: {amount} [{bucket}] {primary}/{detailed}".format(
                date=transaction["date"],
                name=transaction["name"],
                amount=transaction["amount"],
                bucket=transaction["bucket"],
                primary=transaction.get("plaid_primary_category"),
                detailed=transaction.get("plaid_detailed_category"),
            )
        )

    return 0


def request_json(method: str, url: str) -> dict:
    request = Request(url, method=method)
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
        print(f"dashboard smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
