from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query

from app.auth.jwt_validator import JWTValidationError, validate_bearer_token
from app.auth.models import AuthenticatedUser
from app.config import Settings, get_settings
from app.errors import APIError, ErrorCode
from app.utilities.client_user_id import InvalidClientUserIDError, normalize_client_user_id


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def get_authenticated_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    client_user_id: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    if settings.allows_local_identity_bypass:
        candidate = client_user_id or settings.default_client_user_id
        try:
            user_id = normalize_client_user_id(candidate)
        except InvalidClientUserIDError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return AuthenticatedUser(user_id=user_id, auth_method="local")

    token = _extract_bearer_token(authorization)
    if not token:
        raise APIError(
            status_code=401,
            error_code=ErrorCode.AUTH_REQUIRED,
            detail="Authorization header with a Bearer token is required.",
        )

    try:
        user_id = normalize_client_user_id(
            validate_bearer_token(token, settings)
        )
    except JWTValidationError as exc:
        raise APIError(
            status_code=401,
            error_code=ErrorCode.AUTH_INVALID,
            detail=str(exc),
        ) from exc
    except InvalidClientUserIDError as exc:
        raise APIError(
            status_code=401,
            error_code=ErrorCode.AUTH_INVALID,
            detail=str(exc),
        ) from exc

    if client_user_id and client_user_id != user_id:
        raise APIError(
            status_code=403,
            error_code=ErrorCode.AUTH_FORBIDDEN,
            detail="client_user_id does not match the authenticated user.",
        )

    return AuthenticatedUser(user_id=user_id, auth_method="jwt")


def resolve_client_user_id(
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> str:
    return user.user_id
