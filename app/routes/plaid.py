from fastapi import APIRouter, Body, Depends

from app.schemas.plaid import (
    AccountsResponse,
    BalancesResponse,
    CreateLinkTokenRequest,
    CreateLinkTokenResponse,
    ExchangePublicTokenRequest,
    ExchangePublicTokenResponse,
    TransactionsResponse,
)
from app.services.plaid_service import PlaidService, get_plaid_service

router = APIRouter()


@router.post("/create-link-token")
def create_link_token(
    request: CreateLinkTokenRequest = Body(default_factory=CreateLinkTokenRequest),
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> CreateLinkTokenResponse:
    return plaid_service.create_link_token(request)


@router.post("/exchange-public-token")
def exchange_public_token(
    request: ExchangePublicTokenRequest | None = Body(default=None),
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> ExchangePublicTokenResponse:
    return plaid_service.exchange_public_token(request)


@router.get("/accounts")
def get_accounts(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> AccountsResponse:
    return plaid_service.get_accounts()


@router.get("/transactions")
def get_transactions(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> TransactionsResponse:
    return plaid_service.get_transactions()


@router.get("/balances")
def get_balances(
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> BalancesResponse:
    return plaid_service.get_balances()
