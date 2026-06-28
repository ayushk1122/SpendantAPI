from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.db.database import check_database_ready

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    if not check_database_ready(settings):
        return {"status": "not_ready", "database": "unavailable"}
    return {"status": "ready", "database": "ok"}
