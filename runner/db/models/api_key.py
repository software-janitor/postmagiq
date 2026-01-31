"""API Key and Webhook models for Phase 8.

Includes:
- APIKey: API keys with hashed storage, scopes, rate limits
- Webhook: Webhook endpoint registrations
- WebhookDelivery: Delivery attempt records for webhooks
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
import secrets
import hashlib

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# Enums
# =============================================================================


class APIKeyStatus(str, Enum):
    """Status of an API key."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class WebhookStatus(str, Enum):
    """Status of a webhook."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class DeliveryStatus(str, Enum):
    """Status of a webhook delivery attempt."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookEventType(str, Enum):
    """Types of events that can trigger webhooks."""

    POST_CREATED = "post.created"
    POST_UPDATED = "post.updated"
    POST_PUBLISHED = "post.published"
    POST_DELETED = "post.deleted"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_REJECTED = "approval.rejected"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"


# =============================================================================
# API Key
# =============================================================================


class APIKeyBase(SQLModel):
    """Base fields for API keys."""

    name: str = Field(index=True)  # Human-readable name
    description: Optional[str] = None
    scopes: str = Field(default="")  # Comma-separated list of scopes
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_per_day: int = Field(default=10000)
    status: str = Field(default=APIKeyStatus.ACTIVE.value, index=True)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


class APIKey(UUIDModel, APIKeyBase, TimestampMixin, table=True):
    """API key for programmatic access.

    Keys are stored as hashed values for security.
    The actual key is only shown once at creation time.
    """

    __tablename__ = "api_keys"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    created_by_id: UUID = Field(foreign_key="users.id", index=True)

    # Key storage - only store hash, prefix shown for identification
    key_hash: str = Field(index=True)  # SHA-256 hash of the key
    key_prefix: str = Field(max_length=8)  # First 8 chars for identification

    # Usage tracking
    total_requests: int = Field(default=0)
    revoked_at: Optional[datetime] = None
    revoked_by_id: Optional[UUID] = Field(default=None, foreign_key="users.id")

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """Generate a new API key.

        Returns:
            tuple: (full_key, key_prefix, key_hash)
        """
        # Generate a secure random key
        key = f"qx_{secrets.token_urlsafe(32)}"
        prefix = key[:8]
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, prefix, key_hash

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash a key for comparison."""
        return hashlib.sha256(key.encode()).hexdigest()


class APIKeyCreate(APIKeyBase):
    """Schema for creating an API key."""

    workspace_id: UUID
    created_by_id: UUID


class APIKeyRead(APIKeyBase):
    """Schema for reading API key data (without sensitive fields)."""

    id: UUID
    workspace_id: UUID
    created_by_id: UUID
    key_prefix: str
    total_requests: int
    created_at: datetime


# =============================================================================
# Webhook
# =============================================================================


class WebhookBase(SQLModel):
    """Base fields for webhooks."""

    name: str = Field(index=True)
    description: Optional[str] = None
    url: str  # Target URL for webhook delivery
    events: str = Field(default="")  # Comma-separated list of event types
    status: str = Field(default=WebhookStatus.ACTIVE.value, index=True)

    # Delivery settings
    timeout_seconds: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_delay_seconds: int = Field(default=60)

    # Optional headers (JSON string)
    headers: Optional[str] = None


class Webhook(UUIDModel, WebhookBase, TimestampMixin, table=True):
    """Webhook endpoint registration.

    Workspaces can register webhooks to receive event notifications.
    """

    __tablename__ = "webhooks"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    created_by_id: UUID = Field(foreign_key="users.id", index=True)

    # Secret for signing payloads (stored hashed)
    secret_hash: str
    secret_prefix: str = Field(max_length=8)

    # Stats
    total_deliveries: int = Field(default=0)
    successful_deliveries: int = Field(default=0)
    failed_deliveries: int = Field(default=0)
    last_delivery_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None

    @staticmethod
    def generate_secret() -> tuple[str, str, str]:
        """Generate a webhook signing secret.

        Returns:
            tuple: (full_secret, secret_prefix, secret_hash)
        """
        secret = f"whsec_{secrets.token_urlsafe(32)}"
        prefix = secret[:8]
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        return secret, prefix, secret_hash


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook."""

    workspace_id: UUID
    created_by_id: UUID


class WebhookRead(WebhookBase):
    """Schema for reading webhook data."""

    id: UUID
    workspace_id: UUID
    created_by_id: UUID
    secret_prefix: str
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_delivery_at: Optional[datetime]
    created_at: datetime


# =============================================================================
# Webhook Delivery
# =============================================================================


class WebhookDeliveryBase(SQLModel):
    """Base fields for webhook delivery attempts."""

    event_type: str = Field(index=True)
    event_id: str = Field(index=True)  # Unique ID for this event
    payload: str  # JSON payload
    status: str = Field(default=DeliveryStatus.PENDING.value, index=True)

    # Response details
    response_status_code: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: Optional[str] = None

    # Timing
    delivered_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Retry tracking
    attempt_number: int = Field(default=1)
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WebhookDelivery(UUIDModel, WebhookDeliveryBase, TimestampMixin, table=True):
    """Record of a webhook delivery attempt.

    Each delivery attempt creates a new row for audit trail.
    """

    __tablename__ = "webhook_deliveries"

    webhook_id: UUID = Field(foreign_key="webhooks.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)

    # Reference to the resource that triggered the event
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None


class WebhookDeliveryCreate(WebhookDeliveryBase):
    """Schema for creating a webhook delivery."""

    webhook_id: UUID
    workspace_id: UUID
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None


class WebhookDeliveryRead(WebhookDeliveryBase):
    """Schema for reading webhook delivery data."""

    id: UUID
    webhook_id: UUID
    workspace_id: UUID
    resource_type: Optional[str]
    resource_id: Optional[UUID]
    created_at: datetime
