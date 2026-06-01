from fastapi import APIRouter, Depends

from app.services.plaid_service import PlaidService, get_plaid_service

router = APIRouter()


@router.post("/create-link-token")
def create_link_token(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> dict[str, object]:
    return plaid_service.create_link_token()


@router.post("/exchange-public-token")
def exchange_public_token(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> dict[str, object]:
    return plaid_service.exchange_public_token()


@router.get("/accounts")
def get_accounts(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> dict[str, object]:
    return plaid_service.get_accounts()


@router.get("/transactions")
def get_transactions(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> dict[str, object]:
    return plaid_service.get_transactions()


@router.get("/balances")
def get_balances(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> dict[str, object]:
    return plaid_service.get_balances()

