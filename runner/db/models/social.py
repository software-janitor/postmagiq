"""Social media connection and publishing models.

Stores OAuth tokens for LinkedIn, X (Twitter), and Threads,
along with scheduled posts for deferred publishing.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import LargeBinary
from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


class SocialPlatform(str, Enum):
    """Supported social media platforms."""

    linkedin = "linkedin"
    x = "x"
    threads = "threads"


class ScheduledPostStatus(str, Enum):
    """Status of a scheduled post."""

    pending = "pending"  # Waiting to be published
    publishing = "publishing"  # Currently being published
    published = "published"  # Successfully published
    failed = "failed"  # Failed to publish
    cancelled = "cancelled"  # User cancelled


class SocialConnection(UUIDModel, TimestampMixin, table=True):
    """OAuth tokens for social media platforms.

    Stores encrypted access tokens and refresh tokens for each
    platform connection. One connection per user per platform.

    Tokens are encrypted using PostgreSQL pgcrypto (pgp_sym_encrypt).
    Use runner.db.crypto.encrypt_token/decrypt_token to handle encryption.
    """

    __tablename__ = "social_connections"

    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", nullable=False, index=True)
    platform: SocialPlatform = Field(nullable=False)

    # OAuth tokens - encrypted with pgcrypto (stored as bytea)
    access_token: bytes = Field(nullable=False, sa_type=LargeBinary)
    refresh_token: Optional[bytes] = Field(default=None, sa_type=LargeBinary)
    token_secret: Optional[bytes] = Field(default=None, sa_type=LargeBinary)  # OAuth 1.0a
    expires_at: Optional[datetime] = Field(default=None)

    # Platform-specific user info
    platform_user_id: str = Field(nullable=False)  # LinkedIn URN, X user ID, etc.
    platform_username: str = Field(nullable=False)  # For display
    platform_name: Optional[str] = Field(default=None)  # Display name

    # OAuth scopes granted
    scopes: Optional[str] = Field(default=None)  # Comma-separated


class SocialConnectionCreate(SQLModel):
    """Create schema for social connection."""

    user_id: UUID
    workspace_id: UUID
    platform: SocialPlatform
    access_token: str
    refresh_token: Optional[str] = None
    token_secret: Optional[str] = None
    expires_at: Optional[datetime] = None
    platform_user_id: str
    platform_username: str
    platform_name: Optional[str] = None
    scopes: Optional[str] = None


class SocialConnectionRead(SQLModel):
    """Read schema for social connection (no tokens exposed)."""

    id: UUID
    user_id: UUID
    workspace_id: UUID
    platform: SocialPlatform
    platform_user_id: str
    platform_username: str
    platform_name: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class ScheduledPost(UUIDModel, TimestampMixin, table=True):
    """A post scheduled for future publishing.

    Links to a Post and specifies when and where to publish.
    """

    __tablename__ = "scheduled_posts"

    workspace_id: UUID = Field(foreign_key="workspaces.id", nullable=False, index=True)
    post_id: UUID = Field(foreign_key="posts.id", nullable=False, index=True)
    connection_id: UUID = Field(
        foreign_key="social_connections.id", nullable=False, index=True
    )

    # Scheduling
    scheduled_for: datetime = Field(nullable=False, index=True)
    timezone: str = Field(default="UTC", nullable=False)

    # Status tracking
    status: ScheduledPostStatus = Field(
        default=ScheduledPostStatus.pending, nullable=False
    )
    published_at: Optional[datetime] = Field(default=None)
    platform_post_id: Optional[str] = Field(default=None)  # ID on the platform
    platform_post_url: Optional[str] = Field(default=None)  # URL to the post

    # Error tracking
    error_message: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)


class ScheduledPostCreate(SQLModel):
    """Create schema for scheduled post."""

    workspace_id: UUID
    post_id: UUID
    connection_id: UUID
    scheduled_for: datetime
    timezone: str = "UTC"


class ScheduledPostRead(SQLModel):
    """Read schema for scheduled post."""

    id: UUID
    workspace_id: UUID
    post_id: UUID
    connection_id: UUID
    scheduled_for: datetime
    timezone: str
    status: ScheduledPostStatus
    published_at: Optional[datetime]
    platform_post_id: Optional[str]
    platform_post_url: Optional[str]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: Optional[datetime]


class PublishResult(SQLModel):
    """Result of a publish operation."""

    success: bool
    platform: SocialPlatform
    post_url: Optional[str] = None
    platform_post_id: Optional[str] = None
    error: Optional[str] = None
