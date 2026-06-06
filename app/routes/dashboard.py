from fastapi import APIRouter, Depends, Query

from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService, get_dashboard_service

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary(
    client_user_id: str = Query(default="spendant-local-user"),
    protected_balance: float | None = Query(default=None),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    return dashboard_service.get_dashboard_summary(
        client_user_id,
        protected_balance=protected_balance,
    )
