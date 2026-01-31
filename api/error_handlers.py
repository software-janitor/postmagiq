"""Global exception handlers for FastAPI.

Provides consistent JSON error response format across all endpoints.
Internal server errors (500s) are logged but not exposed to clients.
"""

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.exceptions import QuillexirException

logger = logging.getLogger(__name__)


def create_error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create standardized error response structure.

    Args:
        code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional context

    Returns:
        Error response dictionary
    """
    error = {
        "code": code,
        "message": message,
    }
    if details:
        error["details"] = details
    return {"error": error}


async def quillexir_exception_handler(
    request: Request, exc: QuillexirException
) -> JSONResponse:
    """Handle QuillexirException and subclasses.

    Logs the error and returns a standardized JSON response.
    """
    logger.warning(
        "API error: %s (code=%s, status=%d, path=%s)",
        exc.message,
        exc.error_code,
        exc.status_code,
        request.url.path,
        extra={"details": exc.details},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=exc.error_code,
            message=exc.message,
            details=exc.details if exc.details else None,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors.

    Converts FastAPI's validation errors to our standard format.
    """
    # Extract field-level errors
    errors = []
    for error in exc.errors():
        loc = ".".join(str(x) for x in error.get("loc", []))
        errors.append(
            {
                "field": loc,
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
        )

    logger.info(
        "Validation error: %d field errors (path=%s)",
        len(errors),
        request.url.path,
    )

    return JSONResponse(
        status_code=400,
        content=create_error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle Starlette/FastAPI HTTPExceptions.

    Converts standard HTTPExceptions to our format for consistency.
    """
    # Map common status codes to error codes
    status_code_map = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_FAILED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
    }

    error_code = status_code_map.get(exc.status_code, "ERROR")
    message = str(exc.detail) if exc.detail else "An error occurred"

    if exc.status_code >= 500:
        logger.error(
            "HTTP error %d: %s (path=%s)",
            exc.status_code,
            message,
            request.url.path,
        )
    else:
        logger.info(
            "HTTP error %d: %s (path=%s)",
            exc.status_code,
            message,
            request.url.path,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=error_code,
            message=message,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions.

    Logs the full traceback but returns a generic message to clients.
    Never exposes internal error details.
    """
    # Log full traceback for debugging
    logger.error(
        "Unhandled exception: %s (path=%s)\n%s",
        str(exc),
        request.url.path,
        traceback.format_exc(),
    )

    return JSONResponse(
        status_code=500,
        content=create_error_response(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(QuillexirException, quillexir_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
