"""Subscription and usage tracking models.

Implements subscription tiers, account subscriptions, usage tracking,
and credit reservations for the multi-tenancy billing system.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


class BillingPeriod(str, Enum):
    """Billing period options."""

    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatus(str, Enum):
    """Status of a subscription."""

    active = "active"
    canceled = "canceled"
    past_due = "past_due"
    trialing = "trialing"
    paused = "paused"


# =============================================================================
# Subscription Tiers
# =============================================================================


class SubscriptionTierBase(SQLModel):
    """Base fields for subscription tiers."""

    name: str = Field(index=True)  # e.g., "Individual", "Team", "Agency"
    slug: str = Field(unique=True, index=True)  # e.g., "individual", "team"
    description: Optional[str] = None

    # Pricing
    price_monthly: Decimal = Field(
        default=Decimal("0"), max_digits=10, decimal_places=2
    )
    price_yearly: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)

    # Limits
    posts_per_month: int = Field(default=0)  # 0 = unlimited
    workspaces_limit: int = Field(default=1)
    members_per_workspace: int = Field(default=1)
    storage_gb: int = Field(default=1)

    # Features
    overage_enabled: bool = Field(default=False)
    overage_rate: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    priority_support: bool = Field(default=False)
    api_access: bool = Field(default=False)
    white_label: bool = Field(default=False)

    # Display
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0)


class SubscriptionTier(UUIDModel, SubscriptionTierBase, TimestampMixin, table=True):
    """Subscription tier table.

    Defines the available subscription plans with their limits and pricing.
    """

    __tablename__ = "subscription_tiers"


class SubscriptionTierRead(SubscriptionTierBase):
    """Schema for reading subscription tier data."""

    id: UUID
    created_at: datetime


# =============================================================================
# Account Subscriptions
# =============================================================================


class AccountSubscriptionBase(SQLModel):
    """Base fields for account subscriptions."""

    status: SubscriptionStatus = Field(default=SubscriptionStatus.active)
    billing_period: BillingPeriod = Field(default=BillingPeriod.monthly)

    # Billing dates
    current_period_start: datetime
    current_period_end: datetime
    canceled_at: Optional[datetime] = None
    cancel_at_period_end: bool = Field(default=False)

    # Stripe integration (nullable until Stripe is connected)
    stripe_subscription_id: Optional[str] = Field(default=None, index=True)
    stripe_customer_id: Optional[str] = Field(default=None, index=True)


class AccountSubscription(
    UUIDModel, AccountSubscriptionBase, TimestampMixin, table=True
):
    """Account subscription table.

    Links a workspace to a subscription tier with billing information.
    """

    __tablename__ = "account_subscriptions"

    workspace_id: UUID = Field(foreign_key="workspaces.id", unique=True, index=True)
    tier_id: UUID = Field(foreign_key="subscription_tiers.id", index=True)


class AccountSubscriptionRead(AccountSubscriptionBase):
    """Schema for reading account subscription data."""

    id: UUID
    workspace_id: UUID
    tier_id: UUID
    created_at: datetime


# =============================================================================
# Usage Tracking
# =============================================================================


class UsageTrackingBase(SQLModel):
    """Base fields for usage tracking."""

    period_start: datetime
    period_end: datetime

    # Usage counts
    posts_created: int = Field(default=0)
    posts_limit: int = Field(default=0)  # Snapshot from tier at period start
    overage_posts: int = Field(default=0)

    # Storage usage in bytes
    storage_used_bytes: int = Field(default=0)
    storage_limit_bytes: int = Field(default=0)

    # API usage (if applicable)
    api_calls: int = Field(default=0)
    api_calls_limit: int = Field(default=0)


class UsageTracking(UUIDModel, UsageTrackingBase, TimestampMixin, table=True):
    """Usage tracking table.

    Tracks resource usage per workspace per billing period.
    """

    __tablename__ = "usage_tracking"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)

    # Composite index for efficient period lookups
    # Note: Index created in migration


class UsageTrackingRead(UsageTrackingBase):
    """Schema for reading usage tracking data."""

    id: UUID
    workspace_id: UUID
    created_at: datetime


# =============================================================================
# Credit Reservations (for idempotent usage tracking)
# =============================================================================


class ReservationStatus(str, Enum):
    """Status of a credit reservation."""

    pending = "pending"
    confirmed = "confirmed"
    released = "released"
    expired = "expired"


class CreditReservationBase(SQLModel):
    """Base fields for credit reservations."""

    # What resource is being reserved
    resource_type: str = Field(index=True)  # e.g., "post", "api_call"
    resource_id: Optional[str] = None  # e.g., post UUID for tracking

    # Reservation details
    amount: int = Field(default=1)
    status: ReservationStatus = Field(default=ReservationStatus.pending)

    # Idempotency
    idempotency_key: str = Field(unique=True, index=True)

    # Expiration
    expires_at: datetime


class CreditReservation(UUIDModel, CreditReservationBase, TimestampMixin, table=True):
    """Credit reservation table.

    Implements idempotent credit reservations to prevent double-counting
    and race conditions in usage tracking.
    """

    __tablename__ = "credit_reservations"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    usage_tracking_id: UUID = Field(foreign_key="usage_tracking.id", index=True)


class CreditReservationRead(CreditReservationBase):
    """Schema for reading credit reservation data."""

    id: UUID
    workspace_id: UUID
    usage_tracking_id: UUID
    created_at: datetime


# =============================================================================
# Tier Features (Feature Flags)
# =============================================================================


class TierFeatureBase(SQLModel):
    """Base fields for tier features."""

    feature_key: str = Field(max_length=50, index=True)  # e.g., 'premium_workflow'
    enabled: bool = Field(default=False)
    config: dict = Field(default_factory=dict, sa_type=JSON)


class TierFeature(UUIDModel, TierFeatureBase, TimestampMixin, table=True):
    """Tier feature table.

    Stores feature flags and configuration per subscription tier.
    Feature keys:
    - basic_workflow: Basic AI workflow access
    - premium_workflow: Premium AI models
    - voice_transcription: Audio transcription
    - youtube_transcription: YouTube URL transcription
    - priority_support: Priority customer support
    - api_access: API key access
    - team_workspaces: Multiple team workspaces
    """

    __tablename__ = "tier_features"

    tier_id: UUID = Field(foreign_key="subscription_tiers.id", index=True)


class TierFeatureRead(TierFeatureBase):
    """Schema for reading tier feature data."""

    id: UUID
    tier_id: UUID
    created_at: datetime
