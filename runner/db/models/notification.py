"""Notification models for Phase 7.

Includes:
- NotificationChannel: available notification delivery channels (email, in-app, etc.)
- NotificationPreference: user preferences per channel and notification type
- Notification: individual notification records
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# Enums
# =============================================================================


class NotificationChannelType(str, Enum):
    """Types of notification delivery channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    # Future: SLACK = "slack", WEBHOOK = "webhook"


class NotificationType(str, Enum):
    """Types of notifications that can be sent."""
    # Approval-related
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_CHANGES_REQUESTED = "approval_changes_requested"
    APPROVAL_COMMENT = "approval_comment"

    # Assignment-related
    POST_ASSIGNED = "post_assigned"
    POST_REASSIGNED = "post_reassigned"

    # Content-related
    POST_STATUS_CHANGED = "post_status_changed"
    POST_DUE_SOON = "post_due_soon"
    POST_OVERDUE = "post_overdue"

    # Workspace/team-related
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    INVITATION_RECEIVED = "invitation_received"
    ROLE_CHANGED = "role_changed"

    # System
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# =============================================================================
# Notification Channel
# =============================================================================


class NotificationChannelBase(SQLModel):
    """Base fields for notification channels."""

    channel_type: str  # NotificationChannelType value
    name: str = Field(index=True)  # e.g., "Email", "In-App"
    description: Optional[str] = None
    is_enabled: bool = Field(default=True)
    config: Optional[str] = None  # JSON config for channel-specific settings


class NotificationChannel(UUIDModel, NotificationChannelBase, TimestampMixin, table=True):
    """Available notification delivery channels.

    System-level definition of channels. Users can then configure preferences
    for each channel.
    """

    __tablename__ = "notification_channels"


class NotificationChannelCreate(NotificationChannelBase):
    """Schema for creating a notification channel."""
    pass


class NotificationChannelRead(NotificationChannelBase):
    """Schema for reading a notification channel."""
    id: UUID
    created_at: datetime


# =============================================================================
# Notification Preference
# =============================================================================


class NotificationPreferenceBase(SQLModel):
    """Base fields for notification preferences."""

    notification_type: str  # NotificationType value
    is_enabled: bool = Field(default=True)


class NotificationPreference(UUIDModel, NotificationPreferenceBase, TimestampMixin, table=True):
    """User notification preferences per channel and type.

    Users can enable/disable specific notification types for each channel.
    For example: enable email for approval_requested, disable for post_assigned.
    """

    __tablename__ = "notification_preferences"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    channel_id: UUID = Field(foreign_key="notification_channels.id", index=True)


class NotificationPreferenceCreate(NotificationPreferenceBase):
    """Schema for creating a notification preference."""

    user_id: UUID
    workspace_id: UUID
    channel_id: UUID


class NotificationPreferenceRead(NotificationPreferenceBase):
    """Schema for reading a notification preference."""

    id: UUID
    user_id: UUID
    workspace_id: UUID
    channel_id: UUID
    created_at: datetime


# =============================================================================
# Notification
# =============================================================================


class NotificationBase(SQLModel):
    """Base fields for notifications."""

    notification_type: str  # NotificationType value
    title: str
    message: str
    priority: str = Field(default=NotificationPriority.NORMAL.value)

    # Optional link to related resource
    resource_type: Optional[str] = None  # e.g., "post", "approval_request"
    resource_id: Optional[UUID] = None

    # Additional data as JSON string
    data: Optional[str] = None


class Notification(UUIDModel, NotificationBase, TimestampMixin, table=True):
    """Individual notification records.

    Notifications are created when events occur and delivered via enabled channels.
    Users can mark notifications as read or dismiss them.
    """

    __tablename__ = "notifications"

    # Who receives this notification
    user_id: UUID = Field(foreign_key="users.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)

    # Who triggered the notification (optional - system notifications may not have one)
    actor_id: Optional[UUID] = Field(default=None, foreign_key="users.id")

    # Delivery status
    is_read: bool = Field(default=False, index=True)
    read_at: Optional[datetime] = None
    is_dismissed: bool = Field(default=False)
    dismissed_at: Optional[datetime] = None

    # Delivery tracking
    delivered_via: Optional[str] = None  # JSON list of channels delivered through
    delivered_at: Optional[datetime] = None


class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""

    user_id: UUID
    workspace_id: UUID
    actor_id: Optional[UUID] = None


class NotificationRead(NotificationBase):
    """Schema for reading a notification."""

    id: UUID
    user_id: UUID
    workspace_id: UUID
    actor_id: Optional[UUID]
    is_read: bool
    read_at: Optional[datetime]
    is_dismissed: bool
    dismissed_at: Optional[datetime]
    delivered_via: Optional[str]
    delivered_at: Optional[datetime]
    created_at: datetime
