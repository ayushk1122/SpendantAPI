import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class PlaidItem:
    client_user_id: str
    access_token: str
    item_id: str
    transactions_cursor: str | None


class PlaidItemStore:
    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def save_item(self, client_user_id: str, access_token: str, item_id: str) -> PlaidItem:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO plaid_items (
                    client_user_id,
                    access_token,
                    item_id,
                    transactions_cursor,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, NULL, ?, ?)
                ON CONFLICT(client_user_id) DO UPDATE SET
                    access_token = excluded.access_token,
                    item_id = excluded.item_id,
                    transactions_cursor = NULL,
                    updated_at = excluded.updated_at
                """,
                (client_user_id, access_token, item_id, now, now),
            )

        return PlaidItem(
            client_user_id=client_user_id,
            access_token=access_token,
            item_id=item_id,
            transactions_cursor=None,
        )

    def get_item(self, client_user_id: str) -> PlaidItem | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT client_user_id, access_token, item_id, transactions_cursor
                FROM plaid_items
                WHERE client_user_id = ?
                """,
                (client_user_id,),
            ).fetchone()

        if row is None:
            return None

        return PlaidItem(
            client_user_id=row["client_user_id"],
            access_token=row["access_token"],
            item_id=row["item_id"],
            transactions_cursor=row["transactions_cursor"],
        )

    def update_transactions_cursor(self, client_user_id: str, cursor: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE plaid_items
                SET transactions_cursor = ?, updated_at = ?
                WHERE client_user_id = ?
                """,
                (cursor, now, client_user_id),
            )

    def reset_transaction_sync(self, client_user_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM plaid_transactions
                WHERE client_user_id = ?
                """,
                (client_user_id,),
            )
            connection.execute(
                """
                UPDATE plaid_items
                SET transactions_cursor = NULL, updated_at = ?
                WHERE client_user_id = ?
                """,
                (now, client_user_id),
            )

    def save_transaction_sync(
        self,
        client_user_id: str,
        added: list[dict],
        modified: list[dict],
        removed: list[dict],
        cursor: str,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            for transaction in [*added, *modified]:
                connection.execute(
                    """
                    INSERT INTO plaid_transactions (
                        transaction_id,
                        client_user_id,
                        account_id,
                        name,
                        amount,
                        date,
                        plaid_primary_category,
                        plaid_detailed_category,
                        plaid_category_confidence,
                        category_json,
                        merchant_name,
                        pending,
                        iso_currency_code,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(transaction_id) DO UPDATE SET
                        account_id = excluded.account_id,
                        name = excluded.name,
                        amount = excluded.amount,
                        date = excluded.date,
                        plaid_primary_category = excluded.plaid_primary_category,
                        plaid_detailed_category = excluded.plaid_detailed_category,
                        plaid_category_confidence = excluded.plaid_category_confidence,
                        category_json = excluded.category_json,
                        merchant_name = excluded.merchant_name,
                        pending = excluded.pending,
                        iso_currency_code = excluded.iso_currency_code,
                        updated_at = excluded.updated_at
                    """,
                    (
                        transaction["transaction_id"],
                        client_user_id,
                        transaction["account_id"],
                        transaction["name"],
                        transaction["amount"],
                        transaction["date"],
                        transaction.get("plaid_primary_category"),
                        transaction.get("plaid_detailed_category"),
                        transaction.get("plaid_category_confidence"),
                        json.dumps(transaction.get("category")),
                        transaction.get("merchant_name"),
                        int(transaction.get("pending", False)),
                        transaction.get("iso_currency_code"),
                        now,
                    ),
                )

            for transaction in removed:
                connection.execute(
                    """
                    DELETE FROM plaid_transactions
                    WHERE transaction_id = ? AND client_user_id = ?
                    """,
                    (transaction["transaction_id"], client_user_id),
                )

            connection.execute(
                """
                UPDATE plaid_items
                SET transactions_cursor = ?, updated_at = ?
                WHERE client_user_id = ?
                """,
                (cursor, now, client_user_id),
            )

    def get_transactions(self, client_user_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    transaction_id,
                    account_id,
                    name,
                    amount,
                    date,
                    plaid_primary_category,
                    plaid_detailed_category,
                    plaid_category_confidence,
                    category_json,
                    merchant_name,
                    pending,
                    iso_currency_code
                FROM plaid_transactions
                WHERE client_user_id = ?
                ORDER BY date DESC, updated_at DESC
                """,
                (client_user_id,),
            ).fetchall()

        return [
            {
                "transaction_id": row["transaction_id"],
                "account_id": row["account_id"],
                "name": row["name"],
                "amount": row["amount"],
                "date": row["date"],
                "plaid_primary_category": row["plaid_primary_category"],
                "plaid_detailed_category": row["plaid_detailed_category"],
                "plaid_category_confidence": row["plaid_category_confidence"],
                "category": json.loads(row["category_json"]),
                "merchant_name": row["merchant_name"],
                "pending": bool(row["pending"]),
                "iso_currency_code": row["iso_currency_code"],
            }
            for row in rows
        ]

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS plaid_items (
                    client_user_id TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    transactions_cursor TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS plaid_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    client_user_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    plaid_primary_category TEXT,
                    plaid_detailed_category TEXT,
                    plaid_category_confidence TEXT,
                    category_json TEXT NOT NULL,
                    merchant_name TEXT,
                    pending INTEGER NOT NULL,
                    iso_currency_code TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plaid_transactions_client_user_id
                ON plaid_transactions(client_user_id)
                """
            )
            self._ensure_column(
                connection,
                "plaid_transactions",
                "plaid_primary_category",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "plaid_transactions",
                "plaid_detailed_category",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "plaid_transactions",
                "plaid_category_confidence",
                "TEXT",
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.storage_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )
