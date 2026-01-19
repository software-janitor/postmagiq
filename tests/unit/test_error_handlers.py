"""Tests for API error handling and exception classes."""

import asyncio
import pytest
from unittest.mock import MagicMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.exceptions import (
    QuillexirException,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ConflictError,
)
from api.error_handlers import (
    create_error_response,
    quillexir_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    register_error_handlers,
)
from api.responses import (
    ErrorResponse,
    ErrorContent,
    PaginatedResponse,
    SuccessResponse,
)


class SyncTestClient:
    """Synchronous wrapper around httpx AsyncClient for testing."""

    def __init__(self, app):
        self.app = app
        self.transport = ASGITransport(app=app)
        self.base_url = "http://testserver"

    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _request(self, method: str, url: str, **kwargs):
        """Make async request."""
        async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
            response = await client.request(method, url, **kwargs)
            return response

    def get(self, url: str, **kwargs):
        return self._run_async(self._request("GET", url, **kwargs))


class TestExceptionClasses:
    """Tests for custom exception classes."""

    def test_quillexir_exception_defaults(self):
        """QuillexirException has correct default values."""
        exc = QuillexirException()
        assert exc.message == "An unexpected error occurred"
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.details == {}
        assert exc.status_code == 500

    def test_quillexir_exception_custom_values(self):
        """QuillexirException accepts custom values."""
        exc = QuillexirException(
            message="Custom error",
            error_code="CUSTOM_CODE",
            details={"key": "value"},
        )
        assert exc.message == "Custom error"
        assert exc.error_code == "CUSTOM_CODE"
        assert exc.details == {"key": "value"}

    def test_quillexir_exception_to_dict(self):
        """to_dict returns correct structure."""
        exc = QuillexirException(
            message="Test error",
            error_code="TEST_CODE",
            details={"field": "value"},
        )
        result = exc.to_dict()
        assert result == {
            "code": "TEST_CODE",
            "message": "Test error",
            "details": {"field": "value"},
        }

    def test_quillexir_exception_to_dict_no_details(self):
        """to_dict omits details when empty."""
        exc = QuillexirException(message="Test error")
        result = exc.to_dict()
        assert "details" not in result

    def test_not_found_error(self):
        """NotFoundError has correct defaults."""
        exc = NotFoundError()
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert exc.message == "Resource not found"

    def test_not_found_error_custom_message(self):
        """NotFoundError accepts custom message."""
        exc = NotFoundError(
            message="Post not found",
            details={"post_id": "123"},
        )
        assert exc.message == "Post not found"
        assert exc.details == {"post_id": "123"}

    def test_validation_error(self):
        """ValidationError has correct defaults."""
        exc = ValidationError()
        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.message == "Validation failed"

    def test_authentication_error(self):
        """AuthenticationError has correct defaults."""
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_FAILED"
        assert exc.message == "Authentication required"

    def test_authorization_error(self):
        """AuthorizationError has correct defaults."""
        exc = AuthorizationError()
        assert exc.status_code == 403
        assert exc.error_code == "FORBIDDEN"
        assert exc.message == "Permission denied"

    def test_rate_limit_error(self):
        """RateLimitError has correct defaults."""
        exc = RateLimitError()
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.message == "Rate limit exceeded"

    def test_conflict_error(self):
        """ConflictError has correct defaults."""
        exc = ConflictError()
        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"
        assert exc.message == "Resource conflict"

    def test_exception_is_raiseable(self):
        """Custom exceptions can be raised and caught."""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError(message="Test not found")
        assert str(exc_info.value) == "Test not found"

    def test_exception_inheritance(self):
        """All custom exceptions inherit from QuillexirException."""
        assert issubclass(NotFoundError, QuillexirException)
        assert issubclass(ValidationError, QuillexirException)
        assert issubclass(AuthenticationError, QuillexirException)
        assert issubclass(AuthorizationError, QuillexirException)
        assert issubclass(RateLimitError, QuillexirException)
        assert issubclass(ConflictError, QuillexirException)


class TestErrorHandlerFunctions:
    """Tests for error handler functions."""

    def test_create_error_response_basic(self):
        """create_error_response returns correct structure."""
        result = create_error_response(
            code="TEST_CODE",
            message="Test message",
        )
        assert result == {
            "error": {
                "code": "TEST_CODE",
                "message": "Test message",
            }
        }

    def test_create_error_response_with_details(self):
        """create_error_response includes details when provided."""
        result = create_error_response(
            code="TEST_CODE",
            message="Test message",
            details={"key": "value"},
        )
        assert result == {
            "error": {
                "code": "TEST_CODE",
                "message": "Test message",
                "details": {"key": "value"},
            }
        }

    def test_quillexir_exception_handler(self):
        """quillexir_exception_handler returns correct response."""
        import json

        request = MagicMock()
        request.url.path = "/api/test"
        exc = NotFoundError(
            message="Post not found",
            details={"post_id": "123"},
        )

        # Run async handler synchronously
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(quillexir_exception_handler(request, exc))
        finally:
            loop.close()

        assert response.status_code == 404
        body = json.loads(response.body)
        assert body == {
            "error": {
                "code": "NOT_FOUND",
                "message": "Post not found",
                "details": {"post_id": "123"},
            }
        }

    def test_http_exception_handler(self):
        """http_exception_handler converts HTTPException to standard format."""
        import json

        request = MagicMock()
        request.url.path = "/api/test"
        exc = StarletteHTTPException(status_code=404, detail="Not found")

        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(http_exception_handler(request, exc))
        finally:
            loop.close()

        assert response.status_code == 404
        body = json.loads(response.body)
        assert body == {
            "error": {
                "code": "NOT_FOUND",
                "message": "Not found",
            }
        }

    def test_http_exception_handler_unknown_status(self):
        """http_exception_handler handles unknown status codes."""
        import json

        request = MagicMock()
        request.url.path = "/api/test"
        exc = StarletteHTTPException(status_code=418, detail="I'm a teapot")

        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(http_exception_handler(request, exc))
        finally:
            loop.close()

        assert response.status_code == 418
        body = json.loads(response.body)
        assert body["error"]["code"] == "ERROR"
        assert body["error"]["message"] == "I'm a teapot"

    def test_unhandled_exception_handler(self):
        """unhandled_exception_handler returns generic 500 response."""
        import json

        request = MagicMock()
        request.url.path = "/api/test"
        exc = RuntimeError("Internal database error")

        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(unhandled_exception_handler(request, exc))
        finally:
            loop.close()

        assert response.status_code == 500
        body = json.loads(response.body)
        # Should NOT expose internal error details
        assert body == {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            }
        }


class TestErrorHandlerIntegration:
    """Integration tests using FastAPI app with error handlers."""

    @pytest.fixture
    def app(self):
        """Create test app with error handlers registered."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/not-found")
        async def raise_not_found():
            raise NotFoundError(message="Item not found")

        @app.get("/validation-error")
        async def raise_validation():
            raise ValidationError(
                message="Invalid input",
                details={"field": "email", "reason": "Invalid format"},
            )

        @app.get("/auth-error")
        async def raise_auth():
            raise AuthenticationError()

        @app.get("/forbidden")
        async def raise_forbidden():
            raise AuthorizationError(message="Admin access required")

        @app.get("/rate-limit")
        async def raise_rate_limit():
            raise RateLimitError(
                details={"retry_after": 60},
            )

        @app.get("/conflict")
        async def raise_conflict():
            raise ConflictError(message="Resource already exists")

        @app.get("/http-exception")
        async def raise_http():
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Access denied")

        @app.get("/internal-error")
        async def raise_internal():
            raise RuntimeError("Unexpected database failure")

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client using SyncTestClient wrapper."""
        return SyncTestClient(app)

    def test_not_found_error_response(self, client):
        """NotFoundError returns 404 with correct format."""
        response = client.get("/not-found")
        assert response.status_code == 404
        data = response.json()
        assert data == {
            "error": {
                "code": "NOT_FOUND",
                "message": "Item not found",
            }
        }

    def test_validation_error_response(self, client):
        """ValidationError returns 400 with details."""
        response = client.get("/validation-error")
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["details"]["field"] == "email"

    def test_authentication_error_response(self, client):
        """AuthenticationError returns 401."""
        response = client.get("/auth-error")
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_authorization_error_response(self, client):
        """AuthorizationError returns 403."""
        response = client.get("/forbidden")
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "FORBIDDEN"
        assert data["error"]["message"] == "Admin access required"

    def test_rate_limit_error_response(self, client):
        """RateLimitError returns 429 with retry info."""
        response = client.get("/rate-limit")
        assert response.status_code == 429
        data = response.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert data["error"]["details"]["retry_after"] == 60

    def test_conflict_error_response(self, client):
        """ConflictError returns 409."""
        response = client.get("/conflict")
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "CONFLICT"

    def test_http_exception_converted(self, client):
        """Standard HTTPException is converted to our format."""
        response = client.get("/http-exception")
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "FORBIDDEN"
        assert data["error"]["message"] == "Access denied"

    def test_internal_error_hides_details(self):
        """Unhandled exceptions return generic 500 without exposing details.

        Note: httpx.ASGITransport propagates unhandled exceptions by default,
        so we test the handler function directly instead of through HTTP.
        """
        import json

        request = MagicMock()
        request.url.path = "/internal-error"
        exc = RuntimeError("Unexpected database failure with sensitive info")

        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(unhandled_exception_handler(request, exc))
        finally:
            loop.close()

        assert response.status_code == 500
        data = json.loads(response.body)
        assert data == {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            }
        }
        # Should NOT contain "database" or error details
        assert "database" not in str(data)
        assert "sensitive" not in str(data)


class TestResponseModels:
    """Tests for response Pydantic models."""

    def test_error_response_model(self):
        """ErrorResponse model validates correctly."""
        response = ErrorResponse(
            error=ErrorContent(
                code="NOT_FOUND",
                message="Resource not found",
            )
        )
        assert response.error.code == "NOT_FOUND"
        assert response.error.message == "Resource not found"
        assert response.error.details is None

    def test_error_response_with_details(self):
        """ErrorResponse accepts details."""
        response = ErrorResponse(
            error=ErrorContent(
                code="VALIDATION_ERROR",
                message="Invalid input",
                details={"field": "email"},
            )
        )
        assert response.error.details == {"field": "email"}

    def test_paginated_response_basic(self):
        """PaginatedResponse validates correctly."""
        response = PaginatedResponse[dict](
            items=[{"id": 1}, {"id": 2}],
            total=10,
            page=1,
            per_page=10,
            pages=1,
        )
        assert len(response.items) == 2
        assert response.total == 10
        assert response.page == 1
        assert response.per_page == 10
        assert response.pages == 1

    def test_paginated_response_create(self):
        """PaginatedResponse.create calculates pages correctly."""
        response = PaginatedResponse.create(
            items=[{"id": 1}],
            total=25,
            page=1,
            per_page=10,
        )
        assert response.pages == 3  # ceil(25/10) = 3

    def test_paginated_response_create_empty(self):
        """PaginatedResponse.create handles empty results."""
        response = PaginatedResponse.create(
            items=[],
            total=0,
            page=1,
            per_page=10,
        )
        assert response.pages == 0
        assert response.total == 0

    def test_paginated_response_create_exact_division(self):
        """PaginatedResponse.create handles exact page divisions."""
        response = PaginatedResponse.create(
            items=[{"id": 1}],
            total=30,
            page=1,
            per_page=10,
        )
        assert response.pages == 3  # 30/10 = 3 exactly

    def test_success_response_default(self):
        """SuccessResponse has correct defaults."""
        response = SuccessResponse()
        assert response.success is True
        assert response.message is None

    def test_success_response_with_message(self):
        """SuccessResponse accepts message."""
        response = SuccessResponse(message="Deleted successfully")
        assert response.success is True
        assert response.message == "Deleted successfully"

    def test_error_response_serialization(self):
        """ErrorResponse serializes to correct JSON."""
        response = ErrorResponse(
            error=ErrorContent(
                code="NOT_FOUND",
                message="Resource not found",
            )
        )
        data = response.model_dump()
        assert data == {
            "error": {
                "code": "NOT_FOUND",
                "message": "Resource not found",
                "details": None,
            }
        }

    def test_error_response_json_excludes_none(self):
        """ErrorResponse JSON excludes None values when using exclude_none."""
        response = ErrorResponse(
            error=ErrorContent(
                code="NOT_FOUND",
                message="Resource not found",
            )
        )
        data = response.model_dump(exclude_none=True)
        assert "details" not in data["error"]
