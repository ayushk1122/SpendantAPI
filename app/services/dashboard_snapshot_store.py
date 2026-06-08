import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.dashboard import DashboardSummaryResponse


class DashboardSnapshotStore:
    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def get_snapshot(
        self,
        *,
        client_user_id: str,
        month: str,
    ) -> DashboardSummaryResponse | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM monthly_dashboard_snapshots
                WHERE client_user_id = ? AND month = ?
                """,
                (client_user_id, month),
            ).fetchone()

        if row is None:
            return None

        return DashboardSummaryResponse.model_validate_json(row["payload_json"])

    def save_snapshot(
        self,
        *,
        client_user_id: str,
        month: str,
        summary: DashboardSummaryResponse,
    ) -> DashboardSummaryResponse:
        now = datetime.now(UTC).isoformat()
        payload = summary.model_copy(
            update={
                "month": month,
                "is_historical": True,
                "snapshot_source": "stored",
                "snapshot_finalized_at": now,
            }
        )
        payload_json = payload.model_dump_json()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO monthly_dashboard_snapshots (
                    client_user_id,
                    month,
                    payload_json,
                    finalized_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_user_id, month) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    finalized_at = excluded.finalized_at,
                    updated_at = excluded.updated_at
                """,
                (
                    client_user_id,
                    month,
                    payload_json,
                    now,
                    now,
                    now,
                ),
            )

        return payload

    def list_snapshot_months(self, *, client_user_id: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT month
                FROM monthly_dashboard_snapshots
                WHERE client_user_id = ?
                ORDER BY month DESC
                """,
                (client_user_id,),
            ).fetchall()

        return [row["month"] for row in rows]

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monthly_dashboard_snapshots (
                    client_user_id TEXT NOT NULL,
                    month TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    finalized_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (client_user_id, month)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_monthly_dashboard_snapshots_client_user_id
                ON monthly_dashboard_snapshots(client_user_id)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.storage_path)
        connection.row_factory = sqlite3.Row
        return connection
