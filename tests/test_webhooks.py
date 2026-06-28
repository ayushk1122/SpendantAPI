from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.plaid_item_store import PlaidItemStore
from app.services.plaid_service import PlaidService, get_plaid_service
from app.services.token_vault import TokenVault


def test_webhook_is_idempotent(temp_sqlite_path: str) -> None:
    from app.config import Settings

    settings = Settings.model_validate(
        {
            "APP_ENV": "local",
            "PLAID_CLIENT_ID": "client-id",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "PLAID_STORAGE_PATH": temp_sqlite_path,
            "TOKEN_ENCRYPTION_KEY": "phase-three-token-key",
        }
    )
    vault = TokenVault(settings)
    encrypted, key_version = vault.encrypt("access-token")
    store = PlaidItemStore(temp_sqlite_path)
    store.save_item(
        client_user_id="spendant-local-user",
        encrypted_access_token=encrypted,
        token_key_version=key_version,
        item_id="item-webhook-1",
    )

    service = PlaidService(settings)
    app.dependency_overrides[get_plaid_service] = lambda: service

    payload = {
        "webhook_id": "evt-1",
        "webhook_type": "SYNC_UPDATES_AVAILABLE",
        "item_id": "item-webhook-1",
    }

    with patch.object(service, "sync_transactions_for_item") as sync_mock:
        with TestClient(app) as client:
            first = client.post("/api/plaid/webhook", json=payload)
            second = client.post("/api/plaid/webhook", json=payload)

    app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    sync_mock.assert_called_once_with(
        client_user_id="spendant-local-user",
        item_id="item-webhook-1",
    )
