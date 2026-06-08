from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.schemas.dashboard import (
    DashboardSnapshotMonthsResponse,
    DashboardSummaryResponse,
    FinalizeDashboardSnapshotRequest,
)
from app.services.dashboard_service import DashboardService, get_dashboard_service

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary(
    client_user_id: str = Query(default="spendant-local-user"),
    protected_balance: float | None = Query(default=None),
    month: str | None = Query(
        default=None,
        pattern=r"^\d{4}-\d{2}$",
        description="Dashboard month in YYYY-MM format. Defaults to the current month.",
    ),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    return dashboard_service.get_dashboard_summary(
        client_user_id,
        protected_balance=protected_balance,
        month=month,
    )


@router.post("/snapshots/finalize")
def finalize_dashboard_snapshot(
    client_user_id: str = Query(default="spendant-local-user"),
    month: str = Query(
        pattern=r"^\d{4}-\d{2}$",
        description="Completed month to finalize in YYYY-MM format.",
    ),
    request: FinalizeDashboardSnapshotRequest = Body(default_factory=FinalizeDashboardSnapshotRequest),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    try:
        return dashboard_service.finalize_month_snapshot(
            client_user_id=client_user_id,
            month=month,
            protected_balance=request.protected_balance,
            money_destinations=request.money_destinations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/snapshots/months")
def get_dashboard_snapshot_months(
    client_user_id: str = Query(default="spendant-local-user"),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSnapshotMonthsResponse:
    return DashboardSnapshotMonthsResponse(
        months=dashboard_service.list_snapshot_months(client_user_id=client_user_id)
    )
