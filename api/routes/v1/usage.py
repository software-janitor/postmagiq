"""Usage and subscription routes for workspace billing.

Routes for checking usage limits, subscription status, and available tiers.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import get_current_user, require_scope
from api.auth.scopes import Scope
from api.services.usage_service import UsageService
from runner.db.models import User, UserRole

router = APIRouter(prefix="/v1/w/{workspace_id}/usage", tags=["usage"])

usage_service = UsageService()


class UsageSummaryResponse(BaseModel):
    """Response model for usage summary."""

    period_start: str
    period_end: str
    posts: dict
    storage: dict
    api_calls: dict
    subscription: dict


class TierResponse(BaseModel):
    """Response model for subscription tier."""

    id: str
    name: str
    slug: str
    description: Optional[str]
    price_monthly: float
    price_yearly: float
    posts_per_month: int
    workspaces_limit: int
    members_per_workspace: int
    storage_gb: int
    overage_enabled: bool
    priority_support: bool
    api_access: bool
    white_label: bool


@router.get("", response_model=UsageSummaryResponse)
async def get_usage_summary(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Get usage summary for the current billing period.

    Returns usage stats for posts, storage, and API calls along with
    the current subscription tier information.

    If the user is an owner with view_as_tier_id set, the response will
    show limits as if they were on that tier (for testing/preview purposes).
    """
    summary = usage_service.get_usage_summary(workspace_id)

    # Owner tier simulation: override tier info in response if view_as_tier_id is set
    if current_user.role == UserRole.owner and current_user.view_as_tier_id:
        simulated_tier = usage_service.get_tier(current_user.view_as_tier_id)
        if simulated_tier:
            # Override subscription tier info with simulated tier
            summary["subscription"] = {
                "tier_name": f"{simulated_tier.name} (Simulated)",
                "tier_slug": simulated_tier.slug,
                "status": "simulated",
                "overage_enabled": simulated_tier.overage_enabled,
            }
            # Override limits with simulated tier's limits
            summary["posts"]["limit"] = simulated_tier.posts_per_month
            summary["posts"]["unlimited"] = simulated_tier.posts_per_month == 0
            summary["storage"]["limit_bytes"] = simulated_tier.storage_gb * 1024 * 1024 * 1024
            summary["storage"]["limit_gb"] = simulated_tier.storage_gb
            summary["storage"]["unlimited"] = simulated_tier.storage_gb == 0
            summary["api_calls"]["limit"] = 10000 if simulated_tier.api_access else 0
            summary["api_calls"]["unlimited"] = simulated_tier.api_access

    return UsageSummaryResponse(**summary)


@router.get("/tiers", response_model=list[TierResponse])
async def list_tiers(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """List all available subscription tiers.

    Returns active tiers ordered by display order.
    """
    tiers = usage_service.list_tiers(active_only=True)
    return [
        TierResponse(
            id=str(tier.id),
            name=tier.name,
            slug=tier.slug,
            description=tier.description,
            price_monthly=float(tier.price_monthly),
            price_yearly=float(tier.price_yearly),
            posts_per_month=tier.posts_per_month,
            workspaces_limit=tier.workspaces_limit,
            members_per_workspace=tier.members_per_workspace,
            storage_gb=tier.storage_gb,
            overage_enabled=tier.overage_enabled,
            priority_support=tier.priority_support,
            api_access=tier.api_access,
            white_label=tier.white_label,
        )
        for tier in tiers
    ]


class CreateSubscriptionRequest(BaseModel):
    """Request to create a subscription."""

    tier_slug: str
    billing_period: str = "monthly"


class SubscriptionResponse(BaseModel):
    """Response for subscription creation."""

    id: str
    tier_slug: str
    status: str
    billing_period: str
    current_period_start: str
    current_period_end: str


@router.post("/subscribe", response_model=SubscriptionResponse)
async def create_subscription(
    workspace_id: UUID,
    request: CreateSubscriptionRequest,
    current_user: User = Depends(require_scope(Scope.WORKSPACE_SETTINGS)),
):
    """Create a subscription for the workspace.

    Requires workspace:settings scope. Creates a new subscription
    with the specified tier and billing period.
    """
    try:
        subscription = usage_service.create_subscription(
            workspace_id=workspace_id,
            tier_slug=request.tier_slug,
            billing_period=request.billing_period,
        )
        tier = usage_service.get_tier(subscription.tier_id)
        return SubscriptionResponse(
            id=str(subscription.id),
            tier_slug=tier.slug if tier else request.tier_slug,
            status=subscription.status,
            billing_period=subscription.billing_period,
            current_period_start=subscription.current_period_start.isoformat(),
            current_period_end=subscription.current_period_end.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
