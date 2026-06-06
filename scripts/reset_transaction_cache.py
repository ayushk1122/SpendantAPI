import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.plaid_item_store import PlaidItemStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clear cached Plaid transactions and reset the sync cursor."
    )
    parser.add_argument("--client-user-id", default="spendant-local-user")
    parser.add_argument(
        "--item-id",
        help="Reset cache for a single linked institution instead of all items.",
    )
    args = parser.parse_args()

    settings = get_settings()
    store = PlaidItemStore(settings.plaid_storage_path)

    if args.item_id:
        item = store.get_item(args.client_user_id, args.item_id)
        if item is None:
            print(
                f"no Plaid item found for client_user_id={args.client_user_id} "
                f"item_id={args.item_id}"
            )
            return 1

        store.reset_transaction_sync(args.client_user_id, args.item_id)
        print(
            f"reset transaction cache for client_user_id={args.client_user_id} "
            f"item_id={args.item_id}"
        )
        return 0

    items = store.get_items(args.client_user_id)
    if not items:
        print(f"no Plaid items found for client_user_id={args.client_user_id}")
        return 1

    store.reset_transaction_sync(args.client_user_id)
    print(f"reset transaction cache for client_user_id={args.client_user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
