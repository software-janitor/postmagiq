"""FastAPI middleware for usage enforcement."""

import logging
from typing import Callable
from uuid import UUID

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.services.usage_service import UsageService

logger = logging.getLogger(__name__)


# Routes that consume post credits
POST_CONSUMING_ROUTES = [
    ("/api/v1/w/", "/posts", "POST"),  # Create post
    ("/api/v1/w/", "/workflow/run", "POST"),  # Run workflow creates content
]

# Routes that consume storage
STORAGE_CONSUMING_ROUTES = [
    ("/api/v1/w/", "/images", "POST"),  # Upload image
]


class UsageEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce usage limits on resource-creating endpoints.

    Checks workspace limits before allowing POST/PUT requests that
    create billable resources (posts, storage, etc).
    """

    def __init__(self, app, usage_service: UsageService = None):
        super().__init__(app)
        self.usage_service = usage_service or UsageService()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check usage limits before processing request.

        For workspace-scoped routes that create resources, verifies
        the workspace has available credits before proceeding.
        """
        # Only check mutating methods
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # Extract workspace ID from path if present
        path = request.url.path
        workspace_id = self._extract_workspace_id(path)

        if not workspace_id:
            return await call_next(request)

        # Check if this route consumes post credits
        if self._matches_route(path, request.method, POST_CONSUMING_ROUTES):
            try:
                within_limit, current, limit = self.usage_service.check_limit(
                    workspace_id, "post", amount=1
                )
                if not within_limit:
                    return JSONResponse(
                        status_code=402,
                        content={
                            "detail": "Post limit exceeded",
                            "error_code": "POST_LIMIT_EXCEEDED",
                            "current": current,
                            "limit": limit,
                            "upgrade_url": "/settings/billing",
                        },
                    )
            except Exception as e:
                # Don't block on service errors - log and continue
                logger.warning(
                    "Usage check failed for workspace %s: %s",
                    workspace_id,
                    str(e),
                )

        # Check if this route consumes storage
        if self._matches_route(path, request.method, STORAGE_CONSUMING_ROUTES):
            # Get content length for storage check
            content_length = request.headers.get("content-length", 0)
            try:
                content_length = int(content_length)
            except (ValueError, TypeError):
                content_length = 0

            if content_length > 0:
                try:
                    within_limit, current, limit = self.usage_service.check_limit(
                        workspace_id, "storage", amount=content_length
                    )
                    if not within_limit:
                        return JSONResponse(
                            status_code=402,
                            content={
                                "detail": "Storage limit exceeded",
                                "error_code": "STORAGE_LIMIT_EXCEEDED",
                                "current_bytes": current,
                                "limit_bytes": limit,
                                "upgrade_url": "/settings/billing",
                            },
                        )
                except Exception as e:
                    logger.warning(
                        "Storage check failed for workspace %s: %s",
                        workspace_id,
                        str(e),
                    )

        return await call_next(request)

    def _extract_workspace_id(self, path: str) -> UUID | None:
        """Extract workspace ID from path like /api/v1/w/{workspace_id}/...

        Args:
            path: Request URL path

        Returns:
            Workspace UUID if found and valid, None otherwise
        """
        if "/api/v1/w/" not in path:
            return None

        try:
            # Path format: /api/v1/w/{workspace_id}/...
            parts = path.split("/api/v1/w/")[1].split("/")
            if parts:
                return UUID(parts[0])
        except (IndexError, ValueError):
            pass
        return None

    def _matches_route(
        self,
        path: str,
        method: str,
        routes: list[tuple[str, str, str]],
    ) -> bool:
        """Check if path matches any route pattern.

        Args:
            path: Request URL path
            method: HTTP method
            routes: List of (prefix, suffix, method) tuples

        Returns:
            True if path matches any route pattern
        """
        for prefix, suffix, route_method in routes:
            if route_method != method:
                continue
            if prefix in path and path.endswith(suffix):
                return True
            if prefix in path and suffix in path:
                return True
        return False
