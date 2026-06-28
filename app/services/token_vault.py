from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings


class TokenVaultError(RuntimeError):
    pass


class TokenVault:
    def __init__(self, settings: Settings) -> None:
        self.default_key_version = settings.token_key_version
        self._fernets: dict[str, Fernet] = {}
        self._load_key(settings.token_key_version, settings.token_encryption_key)

    def encrypt(self, plaintext: str, key_version: str | None = None) -> tuple[str, str]:
        version = key_version or self.default_key_version
        token = self._fernet(version).encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8"), version

    def decrypt(self, ciphertext: str, key_version: str) -> str:
        try:
            plaintext = self._fernet(key_version).decrypt(ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            raise TokenVaultError("Unable to decrypt stored Plaid token.") from exc
        return plaintext.decode("utf-8")

    def _load_key(self, key_version: str, raw_key: str) -> None:
        if key_version in self._fernets:
            return
        self._fernets[key_version] = Fernet(_normalize_fernet_key(raw_key))

    def _fernet(self, key_version: str) -> Fernet:
        fernet = self._fernets.get(key_version)
        if fernet is None:
            raise TokenVaultError(f"Unknown token encryption key version '{key_version}'.")
        return fernet


def _normalize_fernet_key(raw_key: str) -> bytes:
    stripped = raw_key.strip()
    if not stripped:
        raise TokenVaultError("TOKEN_ENCRYPTION_KEY is required.")

    try:
        decoded = base64.urlsafe_b64decode(stripped.encode("utf-8"))
        if len(decoded) == 32:
            return base64.urlsafe_b64encode(decoded)
    except ValueError:
        pass

    digest = hashlib.sha256(stripped.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)
