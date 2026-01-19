"""Custom domain middleware for white-label workspaces.

Detects requests from custom domains and injects workspace context.
This allows white-labeled client portals to function on custom domains
while mapping to the correct workspace.
"""

from typing import Optional
from uuid import UUID

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse

from runner.db.engine import engine
from sqlmodel import Session

from api.services.domain_service import get_workspace_by_custom_domain


# Default domain(s) - requests from these are handled normally
DEFAULT_DOMAINS = {
    "localhost",
    "127.0.0.1",
    "testserver",  # For tests using httpx ASGITransport
    "app.quillexir.com",
    "api.quillexir.com",
    "quillexir.com",
    "api",  # Docker internal hostname
}


class CustomDomainMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and handle requests from custom domains.

    For requests from custom domains (not the default Quillexir domains),
    this middleware:
    1. Extracts the host from the request
    2. Looks up the workspace by verified custom_domain in whitelabel_config
    3. Injects workspace context into request.state for downstream use

    This enables white-labeled client portals to work on agency domains.

    Configuration:
        - DEFAULT_DOMAINS: Set of domains that are handled normally
        - Custom domains must be verified in whitelabel_config

    Middleware Order:
        Should run early, before AuthMiddleware and WorkspaceMiddleware.
    """

    def __init__(self, app, allowed_default_domains: Optional[set[str]] = None):
        """Initialize the middleware.

        Args:
            app: The FastAPI application
            allowed_default_domains: Optional set of default domains to allow.
                If not provided, uses DEFAULT_DOMAINS.
        """
        super().__init__(app)
        self.default_domains = allowed_default_domains or DEFAULT_DOMAINS

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract host from request (without port)
        host = self._extract_host(request)

        if not host:
            # No host header, pass through
            return await call_next(request)

        # Check if this is a default domain
        if self._is_default_domain(host):
            # Normal request, pass through
            return await call_next(request)

        # This is a potential custom domain - look up workspace
        workspace_id = await self._lookup_workspace_by_domain(host)

        if workspace_id is None:
            # Custom domain not found or not verified
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "detail": f"Domain '{host}' is not configured or verified",
                    "error": "custom_domain_not_found",
                },
            )

        # Inject workspace context from custom domain
        request.state.custom_domain = host
        request.state.custom_domain_workspace_id = workspace_id

        return await call_next(request)

    def _extract_host(self, request: Request) -> Optional[str]:
        """Extract the host from the request, stripping port if present.

        Args:
            request: The incoming request

        Returns:
            str: The host without port, or None if not available
        """
        host_header = request.headers.get("host")
        if not host_header:
            return None

        # Strip port if present (e.g., "localhost:8000" -> "localhost")
        host = host_header.split(":")[0].lower()
        return host

    def _is_default_domain(self, host: str) -> bool:
        """Check if the host is a default domain.

        Handles subdomains by checking if the host ends with any default domain.

        Args:
            host: The host to check

        Returns:
            bool: True if this is a default domain
        """
        # Direct match
        if host in self.default_domains:
            return True

        # Check for subdomains of default domains
        for default_domain in self.default_domains:
            if host.endswith(f".{default_domain}"):
                return True

        return False

    async def _lookup_workspace_by_domain(self, domain: str) -> Optional[UUID]:
        """Look up workspace ID by custom domain.

        Args:
            domain: The custom domain to look up

        Returns:
            UUID: Workspace ID if found and verified, None otherwise
        """
        with Session(engine) as session:
            return get_workspace_by_custom_domain(session, domain)


def get_custom_domain_workspace_id(request: Request) -> Optional[UUID]:
    """Helper to get workspace ID from custom domain context.

    Use in route handlers to check if request came from a custom domain.

    Args:
        request: The incoming request

    Returns:
        UUID: Workspace ID if request is from custom domain, None otherwise
    """
    return getattr(request.state, "custom_domain_workspace_id", None)


def get_custom_domain(request: Request) -> Optional[str]:
    """Helper to get the custom domain from request.

    Args:
        request: The incoming request

    Returns:
        str: Custom domain if request is from one, None otherwise
    """
    return getattr(request.state, "custom_domain", None)
