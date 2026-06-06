from fastapi import APIRouter, Body, Depends, Query

from app.schemas.plaid import (
    AccountsResponse,
    BalancesResponse,
    CreateLinkTokenRequest,
    CreateLinkTokenResponse,
    ExchangePublicTokenRequest,
    ExchangePublicTokenResponse,
    PlaidItemsResponse,
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
    request: ExchangePublicTokenRequest,
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> ExchangePublicTokenResponse:
    return plaid_service.exchange_public_token(request)


@router.get("/items")
def get_items(
    client_user_id: str = Query(default="spendant-local-user"),
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> PlaidItemsResponse:
    return plaid_service.get_items(client_user_id)


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    client_user_id: str = Query(default="spendant-local-user"),
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> dict[str, str]:
    plaid_service.delete_item(client_user_id, item_id)
    return {"status": "deleted", "item_id": item_id}


@router.get("/accounts")
def get_accounts(
    client_user_id: str = Query(default="spendant-local-user"),
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> AccountsResponse:
    return plaid_service.get_accounts(client_user_id)


@router.get("/transactions")
def get_transactions(
    client_user_id: str = Query(default="spendant-local-user"),
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> TransactionsResponse:
    return plaid_service.get_transactions(client_user_id)


@router.get("/balances")
def get_balances(
    client_user_id: str = Query(default="spendant-local-user"),
    plaid_service: PlaidService = Depends(get_plaid_service),
) -> BalancesResponse:
    return plaid_service.get_balances(client_user_id)
