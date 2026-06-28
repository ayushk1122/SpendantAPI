from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class WebhookEventStore:
    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def record_event(
        self,
        *,
        event_id: str,
        item_id: str | None,
        webhook_type: str,
        payload: dict,
    ) -> bool:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO webhook_events (
                        event_id,
                        item_id,
                        webhook_type,
                        payload_json,
                        processed_at,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, NULL, ?)
                    """,
                    (
                        event_id,
                        item_id,
                        webhook_type,
                        json.dumps(payload),
                        now,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def mark_processed(self, event_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE webhook_events
                SET processed_at = ?
                WHERE event_id = ?
                """,
                (now, event_id),
            )

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    item_id TEXT,
                    webhook_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    processed_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_webhook_events_item_id
                ON webhook_events(item_id)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.storage_path)
        connection.row_factory = sqlite3.Row
        return connection


def build_webhook_event_id(payload: dict) -> str:
    explicit = payload.get("webhook_id") or payload.get("event_id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    item_id = payload.get("item_id") or "unknown-item"
    webhook_type = payload.get("webhook_type") or payload.get("webhook_code") or "unknown"
    timestamp = payload.get("timestamp") or payload.get("created_at") or time.time()
    return f"{item_id}:{webhook_type}:{timestamp}"


def new_fallback_event_id() -> str:
    return str(uuid.uuid4())
