"""Base authentication provider abstraction.

Defines the interface that all auth providers must implement.
Authentication providers handle token verification and user identity,
while authorization (roles, scopes, features) remains in the local DB.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Session

from runner.db.models import User


@dataclass
class AuthResult:
    """Result of authentication token verification.

    Attributes:
        valid: Whether the token was successfully verified
        user_id: External provider's user ID (e.g., Clerk user_xxx)
        email: User's email from the provider
        full_name: User's display name from the provider
        provider: Name of the auth provider (e.g., "local", "clerk")
        error: Error message if validation failed
        raw_claims: Full JWT claims for debugging/auditing
    """

    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    provider: str = "unknown"
    error: Optional[str] = None
    raw_claims: Optional[dict] = field(default=None)


class BaseAuthProvider(ABC):
    """Abstract base class for authentication providers.

    Auth providers are responsible for:
    1. Verifying authentication tokens (JWT, sessions, etc.)
    2. Extracting user identity from tokens
    3. Creating/finding local user records

    Auth providers are NOT responsible for:
    - Authorization (roles, scopes, permissions)
    - Workspace membership
    - Feature flags or entitlements
    These remain in the local database.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this provider (e.g., 'local', 'clerk')."""
        ...

    @abstractmethod
    async def verify_token(self, token: str) -> AuthResult:
        """Verify an authentication token.

        Args:
            token: The authentication token (typically JWT)

        Returns:
            AuthResult with validation status and user info if valid
        """
        ...

    @abstractmethod
    async def get_or_create_user(
        self, auth_result: AuthResult, session: Session
    ) -> Optional[User]:
        """Get existing user or create new one from auth result.

        For local auth, this looks up by user_id (UUID).
        For external providers, this looks up by external_id or creates
        a new user record linked to the external identity.

        Args:
            auth_result: Successful auth result with user info
            session: Database session for user lookup/creation

        Returns:
            User if found/created, None if auth_result is invalid
        """
        ...

    @property
    @abstractmethod
    def supports_local_auth(self) -> bool:
        """Whether this provider supports local login/register routes.

        Local providers (password-based) return True.
        External providers (Clerk, Auth0, etc.) return False,
        which disables the /login, /register, /forgot-password routes.
        """
        ...
