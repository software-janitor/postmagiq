"""User model for multi-tenancy."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


class UserRole(str, Enum):
    """User-level role that controls feature flags.

    This is different from WorkspaceRole which controls permissions
    within a specific workspace. UserRole controls the overall UX:
    - owner: Full access to all features, internal views, actual costs
    - admin: Extended access (future use)
    - user: Simplified experience, credit-based usage, no internal tooling
    """

    owner = "owner"
    admin = "admin"
    user = "user"


class UserBase(SQLModel):
    """Base user fields shared across Create/Read/Update."""

    full_name: Optional[str] = Field(default=None, index=True)
    email: Optional[str] = Field(default=None, unique=True, index=True)

    @property
    def name(self) -> Optional[str]:
        """Alias for full_name for backward compatibility."""
        return self.full_name


class User(UUIDModel, UserBase, TimestampMixin, table=True):
    """User table - global identity.

    In multi-tenancy, users can belong to multiple workspaces
    via workspace_memberships table (created in Phase 1).
    """

    __tablename__ = "users"

    # Authentication fields (Phase 2)
    password_hash: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    # User-level role for feature flags
    role: UserRole = Field(default=UserRole.user)

    # Default workspace for individual tier users (hide multi-tenancy UX)
    # When set, API routes can infer workspace without explicit workspace_id in URL
    default_workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: Optional[str] = None


class UserRead(UserBase):
    """Schema for reading user data."""

    id: UUID
    created_at: datetime
    is_active: bool = True
    is_superuser: bool = False
    role: UserRole = UserRole.user
    default_workspace_id: Optional[UUID] = None


class PasswordResetToken(UUIDModel, table=True):
    """Password reset tokens for forgot password flow."""

    __tablename__ = "password_reset_tokens"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    used_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
