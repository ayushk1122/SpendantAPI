import argparse
import json
import sys
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Spendant dashboard summary.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--client-user-id", default="spendant-local-user")
    parser.add_argument("--protected-balance", type=float)
    parser.add_argument(
        "--show-buckets",
        action="store_true",
        help="Print bucket totals and sample transactions for each bucket.",
    )
    args = parser.parse_args()

    query_params = {"client_user_id": args.client_user_id}
    if args.protected_balance is not None:
        query_params["protected_balance"] = str(args.protected_balance)
    query = urlencode(query_params)
    summary = request_json("GET", f"{args.base_url}/api/dashboard/summary?{query}")

    print(f"checking balance: {summary['checking_balance']}")
    print(f"income total: {summary['income_total']} (posted {summary.get('income_posted_total', 0)}, upcoming {summary.get('income_upcoming_total', 0)})")
    print(f"housing total: {summary['housing_total']} (posted {summary.get('housing_posted_total', 0)}, upcoming {summary.get('housing_upcoming_total', 0)})")
    print(f"expenses total: {summary['expenses_total']} (posted only)")
    print(f"subscriptions total: {summary['subscriptions_total']} (posted {summary.get('subscriptions_posted_total', 0)}, upcoming {summary.get('subscriptions_upcoming_total', 0)})")
    print(f"card payments total: {summary.get('transfer_total', 0)} (posted {summary.get('credit_card_payments_posted_total', 0)}, upcoming {summary.get('credit_card_payments_upcoming_total', 0)})")
    print(f"safe to move amount: {summary['safe_to_move_amount']}")
    print(f"safe to move today: {summary.get('safe_to_move_today', summary['safe_to_move_amount'])}")
    print(
        "lowest projected balance: "
        f"{summary.get('lowest_projected_balance', summary.get('checking_balance', 0))} "
        f"on {summary.get('lowest_projected_balance_date', 'n/a')}"
    )
    print(f"recurring streams: {len(summary.get('recurring_streams', []))}")
    print(f"credit card obligations: {len(summary.get('credit_card_obligations', []))}")
    print(f"cash flow events: {len(summary.get('cash_flow_events', []))}")

    transactions = summary.get("transactions", [])
    bucket_counts = Counter(transaction["bucket"] for transaction in transactions)
    print("transaction bucket counts:")
    for bucket, count in sorted(bucket_counts.items()):
        print(f"  {bucket}: {count}")

    if args.show_buckets:
        print_bucket_samples(transactions)

    print("first 5 classified transactions:")
    for transaction in transactions[:5]:
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


def print_bucket_samples(transactions: list[dict]) -> None:
    buckets: dict[str, list[dict]] = {}
    for transaction in transactions:
        buckets.setdefault(transaction["bucket"], []).append(transaction)

    print("bucket samples:")
    for bucket, bucket_transactions in sorted(buckets.items()):
        print(f"  {bucket}:")
        for transaction in bucket_transactions[:3]:
            print(
                "    - {date} {name}: {amount} ({primary}/{detailed})".format(
                    date=transaction["date"],
                    name=transaction["name"],
                    amount=transaction["amount"],
                    primary=transaction.get("plaid_primary_category"),
                    detailed=transaction.get("plaid_detailed_category"),
                )
            )


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
