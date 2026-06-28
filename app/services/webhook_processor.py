from __future__ import annotations

import logging

from app.services.plaid_item_store import PlaidItemStore
from app.services.plaid_service import PlaidService
from app.services.webhook_event_store import WebhookEventStore

logger = logging.getLogger(__name__)

SUPPORTED_WEBHOOK_TYPES = {
    "SYNC_UPDATES_AVAILABLE",
    "TRANSACTIONS_REMOVED",
    "ITEM_ERROR",
    "PENDING_EXPIRATION",
    "USER_PERMISSION_REVOKED",
}


class WebhookProcessor:
    def __init__(
        self,
        *,
        plaid_service: PlaidService,
        item_store: PlaidItemStore,
        event_store: WebhookEventStore,
    ) -> None:
        self.plaid_service = plaid_service
        self.item_store = item_store
        self.event_store = event_store

    def process(self, payload: dict) -> None:
        webhook_type = str(
            payload.get("webhook_type") or payload.get("webhook_code") or "UNKNOWN"
        ).upper()
        item_id = payload.get("item_id")

        if webhook_type == "SYNC_UPDATES_AVAILABLE" and item_id:
            client_user_id = self.item_store.get_client_user_id_for_item(str(item_id))
            if client_user_id:
                self.plaid_service.sync_transactions_for_item(
                    client_user_id=client_user_id,
                    item_id=str(item_id),
                )
            else:
                logger.warning("webhook sync skipped unknown item_id=%s", item_id)
            return

        if webhook_type in {"ITEM_ERROR", "PENDING_EXPIRATION", "USER_PERMISSION_REVOKED"}:
            logger.warning(
                "webhook item status update item_id=%s webhook_type=%s payload=%s",
                item_id,
                webhook_type,
                payload,
            )
            return

        if webhook_type == "TRANSACTIONS_REMOVED" and item_id:
            removed_ids = payload.get("removed_transactions") or []
            client_user_id = self.item_store.get_client_user_id_for_item(str(item_id))
            if client_user_id and removed_ids:
                self.item_store.delete_transactions(
                    client_user_id=client_user_id,
                    transaction_ids=[str(value) for value in removed_ids],
                )
            return

        logger.info("webhook ignored webhook_type=%s item_id=%s", webhook_type, item_id)
