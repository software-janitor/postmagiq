"""Authentication service for user registration, login, and session management."""

import re
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select

import secrets

from api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from api.auth.password import hash_password, verify_password
from runner.db.models import (
    User, UserRole, ActiveSession, PasswordResetToken,
    Workspace, WorkspaceMembership, WorkspaceRole, InviteStatus,
    SubscriptionTier, AccountSubscription, SubscriptionStatus, BillingPeriod,
)


class AuthService:
    """Service for authentication operations.

    Handles user registration, authentication, and session management.
    Uses SQLModel for database access.
    """

    def __init__(self, session: Session):
        """Initialize with a SQLModel session.

        Args:
            session: SQLModel Session for database operations
        """
        self._session = session

    def register(
        self,
        email: str,
        password: str,
        full_name: str,
    ) -> User:
        """Register a new user.

        Args:
            email: User email address (unique)
            password: Plain text password (will be hashed)
            full_name: User's full name

        Returns:
            Created User instance

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing = self._session.exec(
            select(User).where(User.email == email)
        ).first()
        if existing:
            raise ValueError("Email already registered")

        # Check if this is the first user - they become the owner
        user_count = self._session.exec(select(User)).first()
        is_first_user = user_count is None

        # Create user with hashed password
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=is_first_user,  # First user is also superuser
            role=UserRole.owner if is_first_user else UserRole.user,
        )
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)

        # Create a personal workspace for the user
        workspace = self._create_user_workspace(user)

        return user

    def _create_user_workspace(self, user: User) -> Workspace:
        """Create a personal workspace for a new user.

        Also creates a free tier subscription for the workspace.

        Args:
            user: The user to create a workspace for

        Returns:
            Created Workspace instance
        """
        # Generate a unique slug from the user's name or email
        base_slug = self._generate_slug(user.name or user.email.split("@")[0])
        slug = self._ensure_unique_slug(base_slug)

        # Create workspace
        workspace = Workspace(
            name=f"{user.name}'s Workspace" if user.name else "My Workspace",
            slug=slug,
            owner_id=user.id,
            description="Personal workspace",
        )
        self._session.add(workspace)
        self._session.commit()
        self._session.refresh(workspace)

        # Create membership linking user to workspace as owner
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=user.id,
            email=user.email,
            role=WorkspaceRole.owner,
            invite_status=InviteStatus.accepted,
            accepted_at=datetime.utcnow(),
        )
        self._session.add(membership)
        self._session.commit()

        # Create free tier subscription for the workspace
        self._create_free_subscription(workspace)

        return workspace

    def _create_free_subscription(self, workspace: Workspace) -> Optional[AccountSubscription]:
        """Create a free tier subscription for a workspace.

        Args:
            workspace: The workspace to create a subscription for

        Returns:
            Created AccountSubscription or None if free tier not found
        """
        # Find the free tier
        free_tier = self._session.exec(
            select(SubscriptionTier).where(
                SubscriptionTier.slug == "free",
                SubscriptionTier.is_active == True,
            )
        ).first()

        if not free_tier:
            # Free tier not available (not migrated yet)
            return None

        # Create subscription with monthly billing period starting now
        now = datetime.utcnow()
        period_end = now.replace(day=1)
        if now.month == 12:
            period_end = period_end.replace(year=now.year + 1, month=1)
        else:
            period_end = period_end.replace(month=now.month + 1)

        subscription = AccountSubscription(
            workspace_id=workspace.id,
            tier_id=free_tier.id,
            status=SubscriptionStatus.active,
            billing_period=BillingPeriod.monthly,
            current_period_start=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            current_period_end=period_end,
        )
        self._session.add(subscription)
        self._session.commit()
        self._session.refresh(subscription)
        return subscription

    def _generate_slug(self, name: str) -> str:
        """Generate a URL-safe slug from a name.

        Args:
            name: Name to convert to slug

        Returns:
            URL-safe slug
        """
        # Convert to lowercase, replace spaces with hyphens
        slug = name.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug or "workspace"

    def _ensure_unique_slug(self, base_slug: str) -> str:
        """Ensure a slug is unique by appending a suffix if needed.

        Args:
            base_slug: The base slug to make unique

        Returns:
            Unique slug
        """
        slug = base_slug
        existing = self._session.exec(
            select(Workspace).where(Workspace.slug == slug)
        ).first()

        if not existing:
            return slug

        # Append random suffix to make unique
        suffix = str(uuid4())[:8]
        return f"{base_slug}-{suffix}"

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password.

        Args:
            email: User email address
            password: Plain text password

        Returns:
            User instance if authentication succeeds, None otherwise
        """
        user = self._session.exec(
            select(User).where(User.email == email)
        ).first()

        if not user:
            return None

        if not user.password_hash:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    def create_session(
        self,
        user_id: UUID,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        """Create a new session with access and refresh tokens.

        Args:
            user_id: User UUID
            user_agent: Client user agent string
            ip_address: Client IP address

        Returns:
            Dict with access_token, refresh_token, token_type, and expires_in
        """
        # Create tokens
        token_data = {"sub": str(user_id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Decode refresh token to get JTI for session tracking
        refresh_payload = verify_token(refresh_token)
        if not refresh_payload:
            raise RuntimeError("Failed to create refresh token")

        token_jti = refresh_payload.get("jti")
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        # Store session in database
        active_session = ActiveSession(
            user_id=user_id,
            token_jti=token_jti,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
        )
        self._session.add(active_session)
        self._session.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 30 * 60,  # 30 minutes in seconds
        }

    def revoke_session(self, token_jti: str) -> bool:
        """Revoke a session by its token JTI.

        Args:
            token_jti: JWT ID from the refresh token

        Returns:
            True if session was revoked, False if not found
        """
        active_session = self._session.exec(
            select(ActiveSession).where(ActiveSession.token_jti == token_jti)
        ).first()

        if not active_session:
            return False

        active_session.revoked_at = datetime.utcnow()
        self._session.add(active_session)
        self._session.commit()
        return True

    def validate_session(self, token_jti: str) -> bool:
        """Validate that a session is active (not revoked or expired).

        Args:
            token_jti: JWT ID from the refresh token

        Returns:
            True if session is valid, False otherwise
        """
        active_session = self._session.exec(
            select(ActiveSession).where(ActiveSession.token_jti == token_jti)
        ).first()

        if not active_session:
            return False

        if active_session.revoked_at is not None:
            return False

        if active_session.expires_at < datetime.utcnow():
            return False

        return True

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by their ID.

        Args:
            user_id: User UUID

        Returns:
            User instance if found, None otherwise
        """
        return self._session.get(User, user_id)

    def revoke_all_user_sessions(self, user_id: UUID) -> int:
        """Revoke all active sessions for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of sessions revoked
        """
        sessions = self._session.exec(
            select(ActiveSession).where(
                ActiveSession.user_id == user_id,
                ActiveSession.revoked_at.is_(None),
            )
        ).all()

        now = datetime.utcnow()
        for session in sessions:
            session.revoked_at = now
            self._session.add(session)

        self._session.commit()
        return len(sessions)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email.

        Args:
            email: User email address

        Returns:
            User instance if found, None otherwise
        """
        return self._session.exec(
            select(User).where(User.email == email)
        ).first()

    def create_password_reset_token(self, user_id: UUID) -> str:
        """Create a password reset token for a user.

        Invalidates any existing tokens for the user.

        Args:
            user_id: User UUID

        Returns:
            The reset token string
        """
        # Invalidate existing tokens for this user
        existing_tokens = self._session.exec(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
        ).all()
        for token in existing_tokens:
            token.used_at = datetime.utcnow()
            self._session.add(token)

        # Create new token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )
        self._session.add(reset_token)
        self._session.commit()

        return token

    def validate_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        """Validate a password reset token.

        Args:
            token: The reset token string

        Returns:
            PasswordResetToken if valid, None otherwise
        """
        reset_token = self._session.exec(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        ).first()

        if not reset_token:
            return None

        # Check if already used
        if reset_token.used_at is not None:
            return None

        # Check if expired
        if reset_token.expires_at < datetime.utcnow():
            return None

        return reset_token

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password using a reset token.

        Args:
            token: The reset token string
            new_password: The new password (plain text)

        Returns:
            True if password was reset, False if token is invalid
        """
        reset_token = self.validate_password_reset_token(token)
        if not reset_token:
            return False

        # Get user
        user = self.get_user_by_id(reset_token.user_id)
        if not user:
            return False

        # Update password
        user.password_hash = hash_password(new_password)
        self._session.add(user)

        # Mark token as used
        reset_token.used_at = datetime.utcnow()
        self._session.add(reset_token)

        # Revoke all existing sessions (force re-login)
        self.revoke_all_user_sessions(user.id)

        self._session.commit()
        return True

    @property
    def session(self) -> Session:
        """Access to the SQLModel session for route handlers that need it."""
        return self._session
