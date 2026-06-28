from fastapi import APIRouter, Depends, Request

from app.services.plaid_service import PlaidService, get_plaid_service
from app.services.webhook_event_store import (
    WebhookEventStore,
    build_webhook_event_id,
    new_fallback_event_id,
)
from app.services.webhook_processor import WebhookProcessor

router = APIRouter()


def get_webhook_event_store(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> WebhookEventStore:
    return WebhookEventStore(plaid_service.settings.plaid_storage_path)


def get_webhook_processor(
    plaid_service: PlaidService = Depends(get_plaid_service),
    event_store: WebhookEventStore = Depends(get_webhook_event_store),
) -> WebhookProcessor:
    return WebhookProcessor(
        plaid_service=plaid_service,
        item_store=plaid_service.item_store,
        event_store=event_store,
    )


@router.post("/webhook")
async def plaid_webhook(
    request: Request,
    processor: WebhookProcessor = Depends(get_webhook_processor),
    event_store: WebhookEventStore = Depends(get_webhook_event_store),
) -> dict[str, str]:
    payload = await request.json()
    event_id = build_webhook_event_id(payload) if isinstance(payload, dict) else new_fallback_event_id()
    if not isinstance(payload, dict):
        payload = {"raw_payload": payload}

    inserted = event_store.record_event(
        event_id=event_id,
        item_id=str(payload.get("item_id")) if payload.get("item_id") else None,
        webhook_type=str(
            payload.get("webhook_type") or payload.get("webhook_code") or "UNKNOWN"
        ),
        payload=payload,
    )
    if not inserted:
        return {"status": "duplicate", "event_id": event_id}

    processor.process(payload)
    event_store.mark_processed(event_id)
    return {"status": "processed", "event_id": event_id}
