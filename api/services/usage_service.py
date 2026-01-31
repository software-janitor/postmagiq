"""Service for usage tracking and credit management.

Handles subscription limits enforcement, usage tracking per billing period,
and idempotent credit reservations.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import uuid

from sqlmodel import Session, select

from runner.db.engine import engine
from runner.db.models import (
    SubscriptionTier,
    AccountSubscription,
    SubscriptionStatus,
    UsageTracking,
    CreditReservation,
    ReservationStatus,
)


class UsageLimitExceeded(Exception):
    """Raised when a workspace exceeds its usage limit."""

    def __init__(self, resource_type: str, limit: int, current: int):
        self.resource_type = resource_type
        self.limit = limit
        self.current = current
        super().__init__(f"{resource_type} limit exceeded: {current}/{limit}")


class UsageService:
    """Service for tracking and enforcing usage limits.

    Provides methods to check limits, reserve credits, and confirm usage
    with idempotency support.
    """

    def get_subscription(self, workspace_id: UUID) -> Optional[AccountSubscription]:
        """Get the active subscription for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            AccountSubscription if found, None otherwise
        """
        with Session(engine) as session:
            statement = select(AccountSubscription).where(
                AccountSubscription.workspace_id == workspace_id,
                AccountSubscription.status == SubscriptionStatus.active,
            )
            subscription = session.exec(statement).first()
            if subscription:
                session.expunge(subscription)
            return subscription

    def get_tier(self, tier_id: UUID) -> Optional[SubscriptionTier]:
        """Get a subscription tier by ID.

        Args:
            tier_id: SubscriptionTier UUID

        Returns:
            SubscriptionTier if found, None otherwise
        """
        with Session(engine) as session:
            tier = session.get(SubscriptionTier, tier_id)
            if tier:
                session.expunge(tier)
            return tier

    def get_tier_by_slug(self, slug: str) -> Optional[SubscriptionTier]:
        """Get a subscription tier by slug.

        Args:
            slug: Tier slug (e.g., 'individual', 'team', 'agency')

        Returns:
            SubscriptionTier if found, None otherwise
        """
        with Session(engine) as session:
            statement = select(SubscriptionTier).where(
                SubscriptionTier.slug == slug,
                SubscriptionTier.is_active,
            )
            tier = session.exec(statement).first()
            if tier:
                session.expunge(tier)
            return tier

    def list_tiers(self, active_only: bool = True) -> list[SubscriptionTier]:
        """List all subscription tiers.

        Args:
            active_only: If True, only return active tiers

        Returns:
            List of SubscriptionTier objects ordered by display_order
        """
        with Session(engine) as session:
            statement = select(SubscriptionTier).order_by(
                SubscriptionTier.display_order
            )
            if active_only:
                statement = statement.where(SubscriptionTier.is_active)
            tiers = list(session.exec(statement).all())
            for t in tiers:
                session.expunge(t)
            return tiers

    def get_or_create_usage_period(self, workspace_id: UUID) -> UsageTracking:
        """Get or create usage tracking for the current billing period.

        Args:
            workspace_id: Workspace UUID

        Returns:
            UsageTracking for the current period
        """
        with Session(engine) as session:
            # Get subscription to determine period
            sub_statement = select(AccountSubscription).where(
                AccountSubscription.workspace_id == workspace_id,
            )
            subscription = session.exec(sub_statement).first()

            if subscription:
                period_start = subscription.current_period_start
                period_end = subscription.current_period_end
            else:
                # Default to current month for workspaces without subscription
                now = datetime.utcnow()
                period_start = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                if now.month == 12:
                    period_end = period_start.replace(year=now.year + 1, month=1)
                else:
                    period_end = period_start.replace(month=now.month + 1)

            # Look for existing usage record
            usage_statement = select(UsageTracking).where(
                UsageTracking.workspace_id == workspace_id,
                UsageTracking.period_start == period_start,
                UsageTracking.period_end == period_end,
            )
            usage = session.exec(usage_statement).first()

            if not usage:
                # Get tier limits to snapshot
                # Default to free tier limits (5 posts, 1GB storage) if no subscription
                tier_limits = {
                    "posts_limit": 5,  # Free tier default
                    "storage_limit_bytes": 1
                    * 1024
                    * 1024
                    * 1024,  # 1GB free tier default
                    "api_calls_limit": 0,
                }
                if subscription:
                    tier = session.get(SubscriptionTier, subscription.tier_id)
                    if tier:
                        tier_limits["posts_limit"] = tier.posts_per_month
                        tier_limits["storage_limit_bytes"] = (
                            tier.storage_gb * 1024 * 1024 * 1024
                        )
                        tier_limits["api_calls_limit"] = 10000 if tier.api_access else 0

                usage = UsageTracking(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    period_start=period_start,
                    period_end=period_end,
                    posts_limit=tier_limits["posts_limit"],
                    storage_limit_bytes=tier_limits["storage_limit_bytes"],
                    api_calls_limit=tier_limits["api_calls_limit"],
                )
                session.add(usage)
                session.commit()
                session.refresh(usage)

            session.expunge(usage)
            return usage

    def check_limit(
        self,
        workspace_id: UUID,
        resource_type: str,
        amount: int = 1,
    ) -> tuple[bool, int, int]:
        """Check if a resource usage is within limits.

        Args:
            workspace_id: Workspace UUID
            resource_type: 'post', 'storage', or 'api_call'
            amount: Amount to check against limit

        Returns:
            Tuple of (within_limit, current_usage, limit)
        """
        usage = self.get_or_create_usage_period(workspace_id)

        if resource_type == "post":
            current = usage.posts_created
            limit = usage.posts_limit
        elif resource_type == "storage":
            current = usage.storage_used_bytes
            limit = usage.storage_limit_bytes
        elif resource_type == "api_call":
            current = usage.api_calls
            limit = usage.api_calls_limit
        else:
            return (True, 0, 0)  # Unknown resource type, allow

        # 0 limit means unlimited
        if limit == 0:
            return (True, current, limit)

        return (current + amount <= limit, current, limit)

    def reserve_credit(
        self,
        workspace_id: UUID,
        resource_type: str,
        idempotency_key: str,
        amount: int = 1,
        resource_id: Optional[str] = None,
        expires_minutes: int = 15,
    ) -> CreditReservation:
        """Reserve credit for future usage (idempotent).

        Creates a pending reservation that holds credit against the limit.
        Must be confirmed or released within the expiration time.

        Args:
            workspace_id: Workspace UUID
            resource_type: 'post', 'storage', or 'api_call'
            idempotency_key: Unique key for this reservation
            amount: Amount to reserve
            resource_id: Optional resource identifier
            expires_minutes: Minutes until reservation expires

        Returns:
            CreditReservation object

        Raises:
            UsageLimitExceeded: If reservation would exceed limit
        """
        with Session(engine) as session:
            # Check for existing reservation with same key
            existing_statement = select(CreditReservation).where(
                CreditReservation.idempotency_key == idempotency_key
            )
            existing = session.exec(existing_statement).first()
            if existing:
                session.expunge(existing)
                return existing

            # Get usage tracking
            usage = self.get_or_create_usage_period(workspace_id)

            # Check limit (including pending reservations)
            pending_statement = select(CreditReservation).where(
                CreditReservation.workspace_id == workspace_id,
                CreditReservation.usage_tracking_id == usage.id,
                CreditReservation.resource_type == resource_type,
                CreditReservation.status == ReservationStatus.pending,
                CreditReservation.expires_at > datetime.utcnow(),
            )
            pending = session.exec(pending_statement).all()
            pending_amount = sum(r.amount for r in pending)

            # Check subscription for overage
            sub_statement = select(AccountSubscription).where(
                AccountSubscription.workspace_id == workspace_id,
            )
            subscription = session.exec(sub_statement).first()

            tier = None
            if subscription:
                tier = session.get(SubscriptionTier, subscription.tier_id)

            # Get current and limit
            if resource_type == "post":
                current = usage.posts_created + pending_amount
                limit = usage.posts_limit
            elif resource_type == "storage":
                current = usage.storage_used_bytes + pending_amount
                limit = usage.storage_limit_bytes
            elif resource_type == "api_call":
                current = usage.api_calls + pending_amount
                limit = usage.api_calls_limit
            else:
                current = 0
                limit = 0

            # Check if within limit (0 = unlimited)
            if limit > 0 and current + amount > limit:
                # Check if overage is allowed
                if tier and tier.overage_enabled:
                    pass  # Allow overage
                else:
                    raise UsageLimitExceeded(resource_type, limit, current)

            # Create reservation
            reservation = CreditReservation(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                usage_tracking_id=usage.id,
                resource_type=resource_type,
                resource_id=resource_id,
                amount=amount,
                status=ReservationStatus.pending,
                idempotency_key=idempotency_key,
                expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
            )
            session.add(reservation)
            session.commit()
            session.refresh(reservation)
            session.expunge(reservation)
            return reservation

    def confirm_usage(self, idempotency_key: str) -> bool:
        """Confirm a pending reservation and increment usage.

        Args:
            idempotency_key: The reservation's idempotency key

        Returns:
            True if confirmed, False if not found or already processed
        """
        with Session(engine) as session:
            statement = select(CreditReservation).where(
                CreditReservation.idempotency_key == idempotency_key,
                CreditReservation.status == ReservationStatus.pending,
            )
            reservation = session.exec(statement).first()

            if not reservation:
                return False

            # Update reservation status
            reservation.status = ReservationStatus.confirmed
            session.add(reservation)

            # Update usage tracking
            usage = session.get(UsageTracking, reservation.usage_tracking_id)
            if usage:
                if reservation.resource_type == "post":
                    usage.posts_created += reservation.amount
                    # Check for overage
                    if (
                        usage.posts_limit > 0
                        and usage.posts_created > usage.posts_limit
                    ):
                        usage.overage_posts = usage.posts_created - usage.posts_limit
                elif reservation.resource_type == "storage":
                    usage.storage_used_bytes += reservation.amount
                elif reservation.resource_type == "api_call":
                    usage.api_calls += reservation.amount
                session.add(usage)

            session.commit()
            return True

    def release_reservation(self, idempotency_key: str) -> bool:
        """Release a pending reservation without using the credit.

        Args:
            idempotency_key: The reservation's idempotency key

        Returns:
            True if released, False if not found or already processed
        """
        with Session(engine) as session:
            statement = select(CreditReservation).where(
                CreditReservation.idempotency_key == idempotency_key,
                CreditReservation.status == ReservationStatus.pending,
            )
            reservation = session.exec(statement).first()

            if not reservation:
                return False

            reservation.status = ReservationStatus.released
            session.add(reservation)
            session.commit()
            return True

    def get_usage_summary(self, workspace_id: UUID) -> dict:
        """Get a summary of current usage for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Dict with usage stats and limits
        """
        usage = self.get_or_create_usage_period(workspace_id)
        subscription = self.get_subscription(workspace_id)

        tier = None
        if subscription:
            tier = self.get_tier(subscription.tier_id)

        return {
            "period_start": usage.period_start.isoformat(),
            "period_end": usage.period_end.isoformat(),
            # Credits format (posts_per_month now represents credits)
            "credits": {
                "used": usage.posts_created,
                "limit": usage.posts_limit,
                "remaining": max(0, usage.posts_limit - usage.posts_created),
                "unlimited": usage.posts_limit == 0,
            },
            # Legacy posts format for backwards compatibility
            "posts": {
                "used": usage.posts_created,
                "limit": usage.posts_limit,
                "overage": usage.overage_posts,
                "unlimited": usage.posts_limit == 0,
            },
            "storage": {
                "used_bytes": usage.storage_used_bytes,
                "limit_bytes": usage.storage_limit_bytes,
                "used_gb": round(usage.storage_used_bytes / (1024**3), 2),
                "limit_gb": round(usage.storage_limit_bytes / (1024**3), 2),
                "unlimited": usage.storage_limit_bytes == 0,
            },
            "api_calls": {
                "used": usage.api_calls,
                "limit": usage.api_calls_limit,
                "unlimited": usage.api_calls_limit == 0,
            },
            "subscription": {
                "tier_name": tier.name if tier else "Free",
                "tier_slug": tier.slug if tier else "free",
                "status": subscription.status if subscription else "none",
                "overage_enabled": tier.overage_enabled if tier else False,
            },
            "tier": {
                "name": tier.name if tier else "Free",
                "slug": tier.slug if tier else "free",
            },
        }

    def consume_credits(
        self,
        workspace_id: UUID,
        credits: int,
        idempotency_key: str,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Consume credits for a completed operation.

        This is a convenience method that reserves and immediately confirms credits.
        For operations that may fail, use reserve_credit + confirm_usage instead.

        Args:
            workspace_id: Workspace UUID
            credits: Number of credits to consume
            idempotency_key: Unique key for this operation
            resource_id: Optional resource identifier

        Returns:
            True if credits were consumed

        Raises:
            UsageLimitExceeded: If not enough credits available
        """
        self.reserve_credit(
            workspace_id=workspace_id,
            resource_type="post",  # Credits tracked as posts
            idempotency_key=idempotency_key,
            amount=credits,
            resource_id=resource_id,
        )
        return self.confirm_usage(idempotency_key)

    def can_afford(self, workspace_id: UUID, credits: int) -> tuple[bool, int, int]:
        """Check if workspace can afford a certain number of credits.

        Args:
            workspace_id: Workspace UUID
            credits: Number of credits needed

        Returns:
            Tuple of (can_afford, current_used, limit)
        """
        return self.check_limit(workspace_id, "post", credits)

    def create_subscription(
        self,
        workspace_id: UUID,
        tier_slug: str,
        billing_period: str = "monthly",
    ) -> AccountSubscription:
        """Create a subscription for a workspace.

        Args:
            workspace_id: Workspace UUID
            tier_slug: Subscription tier slug
            billing_period: 'monthly' or 'yearly'

        Returns:
            Created AccountSubscription

        Raises:
            ValueError: If tier not found or workspace already has subscription
        """
        with Session(engine) as session:
            # Check for existing subscription
            existing_statement = select(AccountSubscription).where(
                AccountSubscription.workspace_id == workspace_id,
            )
            if session.exec(existing_statement).first():
                raise ValueError("Workspace already has a subscription")

            # Get tier
            tier_statement = select(SubscriptionTier).where(
                SubscriptionTier.slug == tier_slug,
                SubscriptionTier.is_active,
            )
            tier = session.exec(tier_statement).first()
            if not tier:
                raise ValueError(f"Tier not found: {tier_slug}")

            # Calculate period
            now = datetime.utcnow()
            if billing_period == "yearly":
                period_end = now.replace(year=now.year + 1)
            else:
                if now.month == 12:
                    period_end = now.replace(year=now.year + 1, month=1)
                else:
                    period_end = now.replace(month=now.month + 1)

            subscription = AccountSubscription(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                tier_id=tier.id,
                status=SubscriptionStatus.active,
                billing_period=billing_period,
                current_period_start=now,
                current_period_end=period_end,
            )
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            session.expunge(subscription)
            return subscription
