from enum import Enum

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(str, Enum):
    AUTH_REQUIRED = "auth_required"
    AUTH_INVALID = "auth_invalid"
    AUTH_FORBIDDEN = "auth_forbidden"
    VALIDATION_ERROR = "validation_error"
    PLAID_ITEM_NOT_FOUND = "plaid_item_not_found"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    CONFIGURATION_ERROR = "configuration_error"
    NOT_FOUND = "not_found"
    INTERNAL_ERROR = "internal_error"


class APIErrorResponse(BaseModel):
    error_code: ErrorCode
    detail: str


class APIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error_code: ErrorCode,
        detail: str,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(detail)


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=APIErrorResponse(
            error_code=exc.error_code,
            detail=exc.detail,
        ).model_dump(),
    )
