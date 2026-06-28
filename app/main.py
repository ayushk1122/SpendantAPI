import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import ConfigurationError, get_settings
from app.errors import APIError, ErrorCode, api_error_handler
from app.middleware.request_logging import RequestLoggingMiddleware, configure_logging
from app.routes import dashboard, health, plaid, plaid_webhook
from app.services.plaid_service import ExternalServiceError, PlaidItemNotFoundError


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Spendant API",
    description="Backend foundation for Spendant cash-flow planning.",
    version="0.2.0",
)

app.add_middleware(RequestLoggingMiddleware)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(plaid.router, prefix="/api/plaid", tags=["plaid"])
app.include_router(plaid_webhook.router, prefix="/api/plaid", tags=["plaid"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

app.add_exception_handler(APIError, api_error_handler)


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(
    request: Request,
    exc: ConfigurationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error_code": ErrorCode.CONFIGURATION_ERROR.value,
            "detail": str(exc),
        },
    )


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(
    request: Request,
    exc: ExternalServiceError,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "error_code": ErrorCode.EXTERNAL_SERVICE_ERROR.value,
            "detail": str(exc),
        },
    )


@app.exception_handler(PlaidItemNotFoundError)
async def plaid_item_not_found_error_handler(
    request: Request,
    exc: PlaidItemNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error_code": ErrorCode.PLAID_ITEM_NOT_FOUND.value,
            "detail": str(exc),
        },
    )
