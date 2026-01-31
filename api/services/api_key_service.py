"""API Key service for managing programmatic access.

Provides:
- API key creation with secure hashing
- Key validation and rate limiting
- Key revocation
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from runner.db.models import (
    APIKey,
    APIKeyStatus,
)


class APIKeyServiceError(Exception):
    """Base exception for API key service errors."""

    pass


class KeyNotFoundError(APIKeyServiceError):
    """Raised when an API key is not found."""

    pass


class KeyRevokedError(APIKeyServiceError):
    """Raised when trying to use a revoked key."""

    pass


class KeyExpiredError(APIKeyServiceError):
    """Raised when trying to use an expired key."""

    pass


class RateLimitExceededError(APIKeyServiceError):
    """Raised when rate limit is exceeded."""

    pass


class APIKeyService:
    """Service for managing API keys."""

    def create_key(
        self,
        session: Session,
        workspace_id: UUID,
        created_by_id: UUID,
        name: str,
        description: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_day: int = 10000,
        expires_in_days: Optional[int] = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key.

        Returns:
            tuple: (APIKey model, plaintext key)
            The plaintext key is only returned once at creation.
        """
        # Generate key
        key, prefix, key_hash = APIKey.generate_key()

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            workspace_id=workspace_id,
            created_by_id=created_by_id,
            name=name,
            description=description,
            key_hash=key_hash,
            key_prefix=prefix,
            scopes=",".join(scopes) if scopes else "",
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_day=rate_limit_per_day,
            expires_at=expires_at,
        )

        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        return api_key, key

    def validate_key(
        self,
        session: Session,
        key: str,
    ) -> APIKey:
        """Validate an API key and return the key model.

        Raises:
            KeyNotFoundError: If key doesn't exist
            KeyRevokedError: If key has been revoked
            KeyExpiredError: If key has expired
        """
        key_hash = APIKey.hash_key(key)

        api_key = session.exec(
            select(APIKey).where(APIKey.key_hash == key_hash)
        ).first()

        if not api_key:
            raise KeyNotFoundError("Invalid API key")

        if api_key.status == APIKeyStatus.REVOKED.value:
            raise KeyRevokedError("API key has been revoked")

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            # Mark as expired
            api_key.status = APIKeyStatus.EXPIRED.value
            session.add(api_key)
            session.commit()
            raise KeyExpiredError("API key has expired")

        # Update last used
        api_key.last_used_at = datetime.utcnow()
        api_key.total_requests += 1
        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        return api_key

    def revoke_key(
        self,
        session: Session,
        key_id: UUID,
        workspace_id: UUID,
        revoked_by_id: UUID,
    ) -> APIKey:
        """Revoke an API key."""
        api_key = session.get(APIKey, key_id)

        if not api_key or api_key.workspace_id != workspace_id:
            raise KeyNotFoundError(f"API key {key_id} not found")

        if api_key.status == APIKeyStatus.REVOKED.value:
            raise APIKeyServiceError("API key is already revoked")

        api_key.status = APIKeyStatus.REVOKED.value
        api_key.revoked_at = datetime.utcnow()
        api_key.revoked_by_id = revoked_by_id

        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        return api_key

    def get_workspace_keys(
        self,
        session: Session,
        workspace_id: UUID,
        include_revoked: bool = False,
    ) -> list[APIKey]:
        """Get all API keys for a workspace."""
        stmt = select(APIKey).where(APIKey.workspace_id == workspace_id)

        if not include_revoked:
            stmt = stmt.where(APIKey.status != APIKeyStatus.REVOKED.value)

        stmt = stmt.order_by(APIKey.created_at.desc())

        return list(session.exec(stmt).all())

    def get_key_by_id(
        self,
        session: Session,
        key_id: UUID,
        workspace_id: UUID,
    ) -> APIKey:
        """Get a specific API key by ID."""
        api_key = session.get(APIKey, key_id)

        if not api_key or api_key.workspace_id != workspace_id:
            raise KeyNotFoundError(f"API key {key_id} not found")

        return api_key

    def update_key(
        self,
        session: Session,
        key_id: UUID,
        workspace_id: UUID,
        **updates,
    ) -> APIKey:
        """Update an API key's metadata."""
        api_key = session.get(APIKey, key_id)

        if not api_key or api_key.workspace_id != workspace_id:
            raise KeyNotFoundError(f"API key {key_id} not found")

        # Only allow updating certain fields
        allowed_fields = {
            "name",
            "description",
            "scopes",
            "rate_limit_per_minute",
            "rate_limit_per_day",
        }

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                if field == "scopes" and isinstance(value, list):
                    value = ",".join(value)
                setattr(api_key, field, value)

        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        return api_key

    def has_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """Check if an API key has a specific scope."""
        if not api_key.scopes:
            return False

        key_scopes = set(s.strip() for s in api_key.scopes.split(",") if s.strip())

        # Check for exact match or wildcard
        if required_scope in key_scopes:
            return True

        # Check for wildcard scopes (e.g., "content:*" matches "content:read")
        resource = required_scope.split(":")[0]
        if f"{resource}:*" in key_scopes:
            return True

        # Check for admin scope (matches everything)
        if "admin" in key_scopes or "*" in key_scopes:
            return True

        return False
