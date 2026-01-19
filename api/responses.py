"""Standard response models for API documentation.

Provides Pydantic models that appear in OpenAPI/Swagger docs
for consistent response schemas.
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field


# Generic type for paginated items
T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Individual error detail for validation errors."""

    field: str = Field(description="Field that caused the error")
    message: str = Field(description="Error message")
    type: str = Field(description="Error type code")


class ErrorContent(BaseModel):
    """Error information container."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional error context",
    )


class ErrorResponse(BaseModel):
    """Standard error response format.

    All API errors follow this structure for consistency.

    Example:
        {
            "error": {
                "code": "NOT_FOUND",
                "message": "Resource not found",
                "details": {"resource_type": "post", "id": "123"}
            }
        }
    """

    error: ErrorContent = Field(description="Error information")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Resource not found",
                        "details": {"resource_type": "post", "id": "123"},
                    }
                },
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "details": {
                            "errors": [
                                {
                                    "field": "body.email",
                                    "message": "value is not a valid email address",
                                    "type": "value_error.email",
                                }
                            ]
                        },
                    }
                },
            ]
        }
    }


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper.

    Use with a type parameter to specify the item type:
        PaginatedResponse[PostSummary]

    Attributes:
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        per_page: Number of items per page
        pages: Total number of pages
    """

    items: list[T] = Field(description="Items for the current page")
    total: int = Field(ge=0, description="Total number of items")
    page: int = Field(ge=1, description="Current page number (1-indexed)")
    per_page: int = Field(ge=1, le=100, description="Items per page")
    pages: int = Field(ge=0, description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response with calculated page count.

        Args:
            items: Items for the current page
            total: Total number of items
            page: Current page number
            per_page: Items per page

        Returns:
            PaginatedResponse with pages calculated
        """
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [{"id": "1", "name": "Item 1"}],
                    "total": 25,
                    "page": 1,
                    "per_page": 10,
                    "pages": 3,
                }
            ]
        }
    }


class SuccessResponse(BaseModel):
    """Simple success response for operations without data.

    Use for DELETE or other operations that don't return content.
    """

    success: bool = Field(default=True, description="Operation succeeded")
    message: Optional[str] = Field(
        default=None,
        description="Optional success message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"success": True},
                {"success": True, "message": "Resource deleted successfully"},
            ]
        }
    }
