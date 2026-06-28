from app.config import Settings
from app.services.token_vault import TokenVault


def test_token_vault_encrypts_and_decrypts_round_trip() -> None:
    settings = Settings.model_validate(
        {
            "APP_ENV": "local",
            "PLAID_CLIENT_ID": "client-id",
            "PLAID_SECRET": "secret",
            "PLAID_ENV": "sandbox",
            "TOKEN_ENCRYPTION_KEY": "phase-three-token-key",
            "TOKEN_KEY_VERSION": "v1",
        }
    )
    vault = TokenVault(settings)

    encrypted, key_version = vault.encrypt("access-sandbox-token")
    plaintext = vault.decrypt(encrypted, key_version)

    assert key_version == "v1"
    assert plaintext == "access-sandbox-token"
    assert encrypted != "access-sandbox-token"
