from __future__ import annotations

import time
from typing import Any

import jwt
from jwt import PyJWKClient

from app.config import Settings


class JWTValidationError(ValueError):
    pass


_jwk_clients: dict[str, PyJWKClient] = {}


def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    client = _jwk_clients.get(jwks_url)
    if client is None:
        client = PyJWKClient(jwks_url)
        _jwk_clients[jwks_url] = client
    return client


def validate_bearer_token(token: str, settings: Settings) -> str:
    if not settings.auth_jwks_url:
        raise JWTValidationError("AUTH_JWKS_URL is not configured.")

    try:
        signing_key = _get_jwk_client(settings.auth_jwks_url).get_signing_key_from_jwt(token)
        payload: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
            options={"require": ["exp", "sub"]},
            leeway=30,
        )
    except jwt.PyJWTError as exc:
        raise JWTValidationError("Invalid or expired access token.") from exc

    subject = payload.get(settings.auth_user_id_claim)
    if not isinstance(subject, str) or not subject.strip():
        raise JWTValidationError("Access token is missing a valid user id claim.")

    if payload.get("exp", 0) <= time.time():
        raise JWTValidationError("Access token has expired.")

    return subject.strip()
