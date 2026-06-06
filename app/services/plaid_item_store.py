import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class PlaidItem:
    item_id: str
    client_user_id: str
    access_token: str
    institution_id: str | None
    institution_name: str | None
    transactions_cursor: str | None


class PlaidItemStore:
    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def save_item(
        self,
        client_user_id: str,
        access_token: str,
        item_id: str,
        institution_id: str | None = None,
        institution_name: str | None = None,
    ) -> PlaidItem:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO plaid_items (
                    item_id,
                    client_user_id,
                    access_token,
                    institution_id,
                    institution_name,
                    transactions_cursor,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    client_user_id = excluded.client_user_id,
                    access_token = excluded.access_token,
                    institution_id = excluded.institution_id,
                    institution_name = excluded.institution_name,
                    updated_at = excluded.updated_at
                """,
                (
                    item_id,
                    client_user_id,
                    access_token,
                    institution_id,
                    institution_name,
                    now,
                    now,
                ),
            )

        return PlaidItem(
            item_id=item_id,
            client_user_id=client_user_id,
            access_token=access_token,
            institution_id=institution_id,
            institution_name=institution_name,
            transactions_cursor=None,
        )

    def get_items(self, client_user_id: str) -> list[PlaidItem]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    item_id,
                    client_user_id,
                    access_token,
                    institution_id,
                    institution_name,
                    transactions_cursor
                FROM plaid_items
                WHERE client_user_id = ?
                ORDER BY created_at ASC
                """,
                (client_user_id,),
            ).fetchall()

        return [self._row_to_item(row) for row in rows]

    def get_item(self, client_user_id: str, item_id: str) -> PlaidItem | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    item_id,
                    client_user_id,
                    access_token,
                    institution_id,
                    institution_name,
                    transactions_cursor
                FROM plaid_items
                WHERE client_user_id = ? AND item_id = ?
                """,
                (client_user_id, item_id),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_item(row)

    def delete_item(self, client_user_id: str, item_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM plaid_transactions
                WHERE client_user_id = ? AND item_id = ?
                """,
                (client_user_id, item_id),
            )
            deleted_transactions = cursor.rowcount

            cursor = connection.execute(
                """
                DELETE FROM plaid_items
                WHERE client_user_id = ? AND item_id = ?
                """,
                (client_user_id, item_id),
            )
            deleted_item = cursor.rowcount

        return deleted_item > 0 or deleted_transactions > 0

    def update_transactions_cursor(
        self,
        client_user_id: str,
        item_id: str,
        cursor: str,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE plaid_items
                SET transactions_cursor = ?, updated_at = ?
                WHERE client_user_id = ? AND item_id = ?
                """,
                (cursor, now, client_user_id, item_id),
            )

    def reset_transaction_sync(
        self,
        client_user_id: str,
        item_id: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            if item_id:
                connection.execute(
                    """
                    DELETE FROM plaid_transactions
                    WHERE client_user_id = ? AND item_id = ?
                    """,
                    (client_user_id, item_id),
                )
                connection.execute(
                    """
                    UPDATE plaid_items
                    SET transactions_cursor = NULL, updated_at = ?
                    WHERE client_user_id = ? AND item_id = ?
                    """,
                    (now, client_user_id, item_id),
                )
                return

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
        item_id: str,
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
                        item_id,
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(transaction_id) DO UPDATE SET
                        item_id = excluded.item_id,
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
                        item_id,
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
                WHERE client_user_id = ? AND item_id = ?
                """,
                (cursor, now, client_user_id, item_id),
            )

    def get_transactions(
        self,
        client_user_id: str,
        item_id: str | None = None,
    ) -> list[dict]:
        query = """
            SELECT
                transaction_id,
                item_id,
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
        """
        params: tuple[str, ...] = (client_user_id,)

        if item_id:
            query += " AND item_id = ?"
            params = (client_user_id, item_id)

        query += " ORDER BY date DESC, updated_at DESC"

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()

        return [
            {
                "transaction_id": row["transaction_id"],
                "item_id": row["item_id"],
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

    def _row_to_item(self, row: sqlite3.Row) -> PlaidItem:
        return PlaidItem(
            item_id=row["item_id"],
            client_user_id=row["client_user_id"],
            access_token=row["access_token"],
            institution_id=row["institution_id"],
            institution_name=row["institution_name"],
            transactions_cursor=row["transactions_cursor"],
        )

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            if self._needs_legacy_migration(connection):
                self._migrate_legacy_schema(connection)

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS plaid_items (
                    item_id TEXT PRIMARY KEY,
                    client_user_id TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    institution_id TEXT,
                    institution_name TEXT,
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
                    item_id TEXT,
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
                CREATE INDEX IF NOT EXISTS idx_plaid_items_client_user_id
                ON plaid_items(client_user_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plaid_transactions_client_user_id
                ON plaid_transactions(client_user_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_plaid_transactions_item_id
                ON plaid_transactions(item_id)
                """
            )
            self._ensure_column(connection, "plaid_transactions", "item_id", "TEXT")
            self._ensure_column(connection, "plaid_items", "institution_id", "TEXT")
            self._ensure_column(connection, "plaid_items", "institution_name", "TEXT")

    def _needs_legacy_migration(self, connection: sqlite3.Connection) -> bool:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'plaid_items'
            """
        ).fetchone()
        if table is None:
            return False

        columns = {
            row["name"]: row["pk"]
            for row in connection.execute("PRAGMA table_info(plaid_items)").fetchall()
        }
        return columns.get("client_user_id") == 1 and columns.get("item_id", 0) != 1

    def _migrate_legacy_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute("ALTER TABLE plaid_items RENAME TO plaid_items_legacy")
        connection.execute(
            """
            CREATE TABLE plaid_items (
                item_id TEXT PRIMARY KEY,
                client_user_id TEXT NOT NULL,
                access_token TEXT NOT NULL,
                institution_id TEXT,
                institution_name TEXT,
                transactions_cursor TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO plaid_items (
                item_id,
                client_user_id,
                access_token,
                institution_id,
                institution_name,
                transactions_cursor,
                created_at,
                updated_at
            )
            SELECT
                item_id,
                client_user_id,
                access_token,
                NULL,
                NULL,
                transactions_cursor,
                created_at,
                updated_at
            FROM plaid_items_legacy
            """
        )
        connection.execute("DROP TABLE plaid_items_legacy")

        self._ensure_column(connection, "plaid_transactions", "item_id", "TEXT")
        connection.execute(
            """
            UPDATE plaid_transactions
            SET item_id = (
                SELECT item_id
                FROM plaid_items
                WHERE plaid_items.client_user_id = plaid_transactions.client_user_id
                LIMIT 1
            )
            WHERE item_id IS NULL
            """
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
