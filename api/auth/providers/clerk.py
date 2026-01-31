"""Clerk authentication provider using JWKS verification.

Verifies JWTs issued by Clerk using their public JWKS endpoint.
Users are created/linked in the local database on first authentication.
"""

import os
import time
from typing import Optional

import httpx
from jose import JWTError, jwt
from sqlmodel import Session, select

from api.auth.providers.base import AuthResult, BaseAuthProvider
from runner.db.models import User


# Configuration from environment
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")

# JWKS cache settings
_jwks_cache: Optional[dict] = None
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # 1 hour in seconds


class ClerkAuthProvider(BaseAuthProvider):
    """Clerk external authentication provider.

    Verifies RS256 JWTs using Clerk's JWKS endpoint.
    Users are looked up by external_id or created on first login.
    """

    def __init__(self) -> None:
        if not CLERK_JWKS_URL:
            raise RuntimeError(
                "CLERK_JWKS_URL environment variable is required when using Clerk auth. "
                "Set it to https://your-domain.clerk.accounts.dev/.well-known/jwks.json"
            )

    @property
    def name(self) -> str:
        return "clerk"

    async def verify_token(self, token: str) -> AuthResult:
        """Verify a Clerk JWT token.

        Fetches JWKS from Clerk (with caching) and verifies the token signature.

        Args:
            token: JWT token from Authorization header

        Returns:
            AuthResult with Clerk user_id and profile info
        """
        try:
            # Get JWKS (cached)
            jwks = await self._get_jwks()

            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                return AuthResult(
                    valid=False,
                    provider=self.name,
                    error="Token missing key ID (kid)",
                )

            # Find matching key
            key = self._find_key(jwks, kid)
            if not key:
                # Try refreshing JWKS in case keys rotated
                jwks = await self._refresh_jwks()
                key = self._find_key(jwks, kid)

            if not key:
                return AuthResult(
                    valid=False,
                    provider=self.name,
                    error=f"No matching key found for kid: {kid}",
                )

            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                options={
                    "verify_aud": False,  # Clerk tokens don't always have aud
                    "verify_iss": False,  # We verify via JWKS URL instead
                },
            )

            # Extract user info from Clerk claims
            # Clerk uses 'sub' for user ID (user_xxx format)
            user_id = payload.get("sub")
            if not user_id:
                return AuthResult(
                    valid=False,
                    provider=self.name,
                    error="Token missing 'sub' claim",
                )

            # Extract additional claims if present
            # Clerk may include these depending on token template
            email = payload.get("email") or payload.get(
                "https://clerk.dev/email"
            )
            full_name = payload.get("name") or payload.get(
                "https://clerk.dev/name"
            )

            return AuthResult(
                valid=True,
                user_id=user_id,
                email=email,
                full_name=full_name,
                provider=self.name,
                raw_claims=payload,
            )

        except JWTError as e:
            return AuthResult(
                valid=False,
                provider=self.name,
                error=f"JWT verification failed: {str(e)}",
            )
        except httpx.HTTPError as e:
            return AuthResult(
                valid=False,
                provider=self.name,
                error=f"Failed to fetch JWKS: {str(e)}",
            )

    async def get_or_create_user(
        self, auth_result: AuthResult, session: Session
    ) -> Optional[User]:
        """Get or create user from Clerk authentication.

        Looks up user by external_id. If not found, creates a new user
        linked to the Clerk identity.

        Args:
            auth_result: Successful auth result from verify_token
            session: Database session

        Returns:
            User (existing or newly created)
        """
        if not auth_result.valid or not auth_result.user_id:
            return None

        # Look up by external_id
        stmt = select(User).where(
            User.external_id == auth_result.user_id,
            User.external_provider == self.name,
        )
        user = session.exec(stmt).first()

        if user:
            # Update user info if changed
            updated = False
            if auth_result.email and user.email != auth_result.email:
                user.email = auth_result.email
                updated = True
            if auth_result.full_name and user.full_name != auth_result.full_name:
                user.full_name = auth_result.full_name
                updated = True

            if updated:
                session.add(user)
                session.commit()
                session.refresh(user)

            if not user.is_active:
                return None

            return user

        # Create new user linked to Clerk identity
        user = User(
            external_id=auth_result.user_id,
            external_provider=self.name,
            email=auth_result.email,
            full_name=auth_result.full_name,
            is_active=True,
            # No password_hash for external auth
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        return user

    @property
    def supports_local_auth(self) -> bool:
        """Clerk provider does not support local login/register."""
        return False

    async def _get_jwks(self) -> dict:
        """Get JWKS, using cache if valid."""
        global _jwks_cache, _jwks_cache_time

        now = time.time()
        if _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
            return _jwks_cache

        return await self._refresh_jwks()

    async def _refresh_jwks(self) -> dict:
        """Fetch fresh JWKS from Clerk."""
        global _jwks_cache, _jwks_cache_time

        async with httpx.AsyncClient() as client:
            response = await client.get(CLERK_JWKS_URL, timeout=10.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = time.time()
            return _jwks_cache

    def _find_key(self, jwks: dict, kid: str) -> Optional[dict]:
        """Find key by ID in JWKS."""
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None
