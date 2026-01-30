"""Local authentication provider using JWT with shared secret.

This provider wraps the existing JWT-based authentication system
for local development and self-hosted deployments.
"""

from typing import Optional
from uuid import UUID

from sqlmodel import Session

from api.auth.jwt import verify_token as jwt_verify_token, VALID_ACCESS_TOKEN_TYPES
from api.auth.providers.base import AuthResult, BaseAuthProvider
from runner.db.models import User


class LocalAuthProvider(BaseAuthProvider):
    """Local JWT authentication provider.

    Uses HS256 JWT tokens with a shared secret (JWT_SECRET).
    Supports password-based login, registration, and password reset.
    """

    @property
    def name(self) -> str:
        return "local"

    async def verify_token(self, token: str) -> AuthResult:
        """Verify a local JWT token.

        Args:
            token: JWT token from Authorization header

        Returns:
            AuthResult with user_id from 'sub' claim
        """
        payload = jwt_verify_token(token)

        if not payload:
            return AuthResult(
                valid=False,
                provider=self.name,
                error="Invalid or expired token",
            )

        # Validate token type
        token_type = payload.get("type", "access")
        if token_type not in VALID_ACCESS_TOKEN_TYPES:
            return AuthResult(
                valid=False,
                provider=self.name,
                error="Invalid token type for this endpoint",
            )

        # Extract user_id from sub claim
        user_id = payload.get("sub")
        if not user_id:
            return AuthResult(
                valid=False,
                provider=self.name,
                error="Invalid token payload: missing 'sub' claim",
            )

        return AuthResult(
            valid=True,
            user_id=user_id,
            provider=self.name,
            raw_claims=payload,
        )

    async def get_or_create_user(
        self, auth_result: AuthResult, session: Session
    ) -> Optional[User]:
        """Load user from database by UUID.

        Local auth always loads existing users - user creation happens
        via the /register route, not during token verification.

        Args:
            auth_result: Successful auth result with user_id (UUID string)
            session: Database session

        Returns:
            User if found, None otherwise
        """
        if not auth_result.valid or not auth_result.user_id:
            return None

        try:
            user_id = UUID(auth_result.user_id)
        except ValueError:
            return None

        user = session.get(User, user_id)

        if user and not user.is_active:
            return None

        return user

    @property
    def supports_local_auth(self) -> bool:
        """Local provider supports login/register routes."""
        return True
