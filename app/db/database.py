from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import Settings, get_settings

_engines: dict[str, Engine] = {}


def get_database_url(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    if resolved.database_url:
        return resolved.database_url
    return f"sqlite:///{resolved.plaid_storage_path}"


def get_engine(settings: Settings | None = None) -> Engine:
    database_url = get_database_url(settings)
    engine = _engines.get(database_url)
    if engine is None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        engine = create_engine(database_url, future=True, connect_args=connect_args)
        _engines[database_url] = engine
    return engine


def check_database_ready(settings: Settings | None = None) -> bool:
    try:
        with get_engine(settings).connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
