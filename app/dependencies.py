from fastapi import Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.utilities.client_user_id import InvalidClientUserIDError, normalize_client_user_id


def resolve_client_user_id(
    client_user_id: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    candidate = client_user_id or settings.default_client_user_id
    try:
        return normalize_client_user_id(candidate)
    except InvalidClientUserIDError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
