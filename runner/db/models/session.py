"""Active session model for authentication."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


class ActiveSessionBase(SQLModel):
    """Base active session fields."""

    user_id: UUID = Field(foreign_key="users.id", index=True)
    token_jti: str = Field(unique=True, index=True)
    user_agent: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    expires_at: datetime
    revoked_at: Optional[datetime] = Field(default=None)


class ActiveSession(UUIDModel, ActiveSessionBase, TimestampMixin, table=True):
    """Active session table for tracking JWT sessions.

    Used for:
    - Session validation (check if token is revoked)
    - Session management (list active sessions)
    - Logout functionality (revoke sessions)
    """

    __tablename__ = "active_sessions"


class ActiveSessionCreate(ActiveSessionBase):
    """Schema for creating a new active session."""

    pass


class ActiveSessionRead(ActiveSessionBase):
    """Schema for reading active session data."""

    id: UUID
    created_at: datetime
