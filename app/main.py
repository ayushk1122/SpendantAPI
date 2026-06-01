from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import ConfigurationError
from app.routes import health, plaid


app = FastAPI(
    title="Spendant API",
    description="Backend foundation for Spendant cash-flow planning.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(plaid.router, prefix="/api/plaid", tags=["plaid"])


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(
    request: Request,
    exc: ConfigurationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )
