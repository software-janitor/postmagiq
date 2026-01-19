"""Authentication middleware.

Extracts JWT from Authorization header and injects user into request.state.
Runs before WorkspaceMiddleware and route handlers.
"""

from typing import Set

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from api.auth.jwt import verify_token
from runner.db.models import User


# Routes that don't require authentication
PUBLIC_ROUTES: Set[str] = {
    "/api/health",
    "/api/health/ready",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",
}

# Route prefixes that are public
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/api/v1/auth/invite",  # Accept invite routes
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and validate JWT authentication.

    For authenticated requests, this middleware:
    1. Extracts JWT from Authorization: Bearer header
    2. Verifies token validity
    3. Loads user from database
    4. Injects user and JWT claims into request.state

    Public routes (login, register, health, etc.) are passed through
    without authentication.

    Note: This middleware does NOT enforce authentication. It only
    extracts user context when present. Use dependencies like
    get_current_user() to enforce authentication on specific routes.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Initialize request state
        request.state.user = None
        request.state.jwt_claims = None
        request.state.workspace = None
        request.state.membership = None
        request.state.workspace_id = None

        # Skip authentication for public routes
        if self._is_public_route(request.url.path):
            return await call_next(request)

        # Extract token from Authorization header
        token = self._extract_token(request)
        if not token:
            # No token - continue without user context
            # Individual routes will enforce auth as needed
            return await call_next(request)

        # Verify token
        payload = verify_token(token)
        if not payload:
            # Invalid token - continue without user context
            # Routes requiring auth will reject the request
            return await call_next(request)

        # Store JWT claims
        request.state.jwt_claims = payload

        # Load user from database
        user = await self._load_user(payload)
        if user:
            request.state.user = user

        return await call_next(request)

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public (no auth required).

        Args:
            path: Request URL path

        Returns:
            True if route is public
        """
        # Check exact matches
        if path in PUBLIC_ROUTES:
            return True

        # Check prefixes
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True

        return False

    def _extract_token(self, request: Request) -> str | None:
        """Extract JWT from Authorization header.

        Args:
            request: FastAPI request

        Returns:
            Token string if present, None otherwise
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        # Expect "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    async def _load_user(self, payload: dict) -> User | None:
        """Load user from database based on JWT payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            User if found, None otherwise
        """
        from uuid import UUID
        from runner.db.engine import engine
        from sqlmodel import Session

        user_id_str = payload.get("sub")
        if not user_id_str:
            return None

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            return None

        with Session(engine) as session:
            user = session.get(User, user_id)
            if user:
                # Detach from session for use outside
                session.expunge(user)
            return user
