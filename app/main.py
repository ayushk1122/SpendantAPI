from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import ConfigurationError, get_settings
from app.routes import dashboard, health, plaid
from app.services.plaid_service import ExternalServiceError, PlaidItemNotFoundError


settings = get_settings()

app = FastAPI(
    title="Spendant API",
    description="Backend foundation for Spendant cash-flow planning.",
    version="0.1.0",
)

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
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(
    request: Request,
    exc: ConfigurationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(
    request: Request,
    exc: ExternalServiceError,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)},
    )


@app.exception_handler(PlaidItemNotFoundError)
async def plaid_item_not_found_error_handler(
    request: Request,
    exc: PlaidItemNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )
