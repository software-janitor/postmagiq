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
from api.services.tier_service import tier_service
from runner.db.models import User

router = APIRouter(prefix="/v1/w/{workspace_id}/usage", tags=["usage"])

usage_service = UsageService()


class CreditsInfo(BaseModel):
    """Credit usage information."""

    used: int
    limit: int
    remaining: int


class FeaturesInfo(BaseModel):
    """Feature availability information."""

    premium_workflow: bool
    voice_transcription: bool
    direct_publishing: bool = False
    youtube_transcription: bool
    priority_support: bool
    api_access: bool
    team_workspaces: bool
    text_limit: int


class TierInfo(BaseModel):
    """Tier information."""

    name: str
    slug: str


class UsageSummaryResponse(BaseModel):
    """Response model for usage summary."""

    period_start: str
    period_end: str
    credits: CreditsInfo
    features: FeaturesInfo
    tier: TierInfo
    # Legacy fields for backwards compatibility
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

    Returns usage stats including credits, features, and tier information.
    """
    summary = usage_service.get_usage_summary(workspace_id)
    features = tier_service.get_features_summary(workspace_id)

    return UsageSummaryResponse(
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        credits=CreditsInfo(
            used=summary["credits"]["used"],
            limit=summary["credits"]["limit"],
            remaining=summary["credits"]["remaining"],
        ),
        features=FeaturesInfo(**features),
        tier=TierInfo(
            name=summary["tier"]["name"],
            slug=summary["tier"]["slug"],
        ),
        # Legacy fields
        posts=summary["posts"],
        storage=summary["storage"],
        api_calls=summary["api_calls"],
        subscription=summary["subscription"],
    )


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


class EstimateRequest(BaseModel):
    """Request for credit estimate."""

    text_length: int


class EstimateResponse(BaseModel):
    """Response for credit estimate."""

    text_length: int
    estimated_credits: int
    credits_remaining: int
    can_proceed: bool


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_credits(
    workspace_id: UUID,
    request: EstimateRequest,
    current_user: User = Depends(get_current_user),
):
    """Estimate credits needed for a workflow run.

    Returns the estimated credits based on text length and the
    workspace's tier, along with whether they can afford it.
    """
    is_premium = tier_service.has_feature(workspace_id, "premium_workflow")
    estimated = tier_service.estimate_credits(request.text_length, is_premium)

    can_afford, used, limit = usage_service.can_afford(workspace_id, estimated)
    remaining = max(0, limit - used) if limit > 0 else 999999

    return EstimateResponse(
        text_length=request.text_length,
        estimated_credits=estimated,
        credits_remaining=remaining,
        can_proceed=can_afford,
    )
