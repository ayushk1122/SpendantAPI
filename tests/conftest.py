from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.services.dashboard_service import DashboardService
from app.services.dashboard_snapshot_store import DashboardSnapshotStore
from tests.fakes import FakePlaidService


@pytest.fixture
def temp_sqlite_path() -> str:
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as handle:
        return handle.name


@pytest.fixture
def snapshot_store(temp_sqlite_path: str) -> DashboardSnapshotStore:
    return DashboardSnapshotStore(temp_sqlite_path)


@pytest.fixture
def fake_plaid_service() -> FakePlaidService:
    return FakePlaidService()


@pytest.fixture
def dashboard_service(
    fake_plaid_service: FakePlaidService,
    snapshot_store: DashboardSnapshotStore,
) -> DashboardService:
    return DashboardService(
        plaid_service=fake_plaid_service,
        snapshot_store=snapshot_store,
    )
