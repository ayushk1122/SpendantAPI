from unittest.mock import MagicMock, patch

from app.config import Settings
from app.schemas.plaid import ExchangePublicTokenRequest
from app.services.plaid_item_store import PlaidItemStore
from app.services.plaid_service import PlaidService


def test_exchange_response_excludes_access_token(temp_sqlite_path: str) -> None:
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
    service = PlaidService(settings)

    mock_response = MagicMock()
    mock_response.to_dict.return_value = {
        "access_token": "access-sandbox-secret",
        "item_id": "item-123",
        "request_id": "req-123",
    }

    with patch.object(service.client, "item_public_token_exchange", return_value=mock_response):
        response = service.exchange_public_token(
            ExchangePublicTokenRequest(
                public_token="public-sandbox-token",
                client_user_id="spendant-local-user",
                institution_id="ins_1",
                institution_name="Test Bank",
            )
        )

    payload = response.model_dump()
    assert "access_token" not in payload
    assert payload["item_id"] == "item-123"

    store = PlaidItemStore(temp_sqlite_path)
    items = store.get_items("spendant-local-user")
    assert len(items) == 1
    assert items[0].encrypted_access_token != "access-sandbox-secret"
    assert items[0].token_key_version == settings.token_key_version
