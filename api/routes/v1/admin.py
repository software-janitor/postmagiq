"""Admin analytics routes.

SaaS owner-only endpoints for viewing metrics across all workspaces.
Routes: /api/v1/admin/analytics/...
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from api.auth.dependencies import (
    CurrentUser,
    require_owner_role,
)
from api.services.admin_analytics_service import (
    AdminAnalyticsService,
    WorkspaceCostSummary,
    DailyCostPoint,
    AgentCostBreakdown,
)
from runner.db.engine import get_session_dependency


router = APIRouter(prefix="/v1/admin/analytics", tags=["admin-analytics"])

analytics_service = AdminAnalyticsService()


# =============================================================================
# Response Models
# =============================================================================


class WorkspaceSummariesResponse(BaseModel):
    """Response for workspace summaries."""

    workspaces: list[WorkspaceCostSummary]
    total_cost_usd: float
    total_tokens: int
    total_runs: int


class TimelineResponse(BaseModel):
    """Response for timeline data."""

    data: list[DailyCostPoint]
    days_back: int


class AgentBreakdownResponse(BaseModel):
    """Response for agent breakdown."""

    agents: list[AgentCostBreakdown]
    total_cost_usd: float


class RefreshResponse(BaseModel):
    """Response for refresh operation."""

    records_updated: int
    message: str


# =============================================================================
# Routes
# =============================================================================


@router.get("/workspaces", response_model=WorkspaceSummariesResponse)
async def get_workspace_summaries(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
    session: Annotated[Session, Depends(get_session_dependency)],
    days_back: int = Query(default=30, ge=1, le=365),
):
    """Get cost summary for all workspaces.

    Requires SaaS owner role.
    """
    summaries = analytics_service.get_workspace_summaries(session, days_back)

    return WorkspaceSummariesResponse(
        workspaces=summaries,
        total_cost_usd=sum(s.total_cost_usd for s in summaries),
        total_tokens=sum(s.total_tokens for s in summaries),
        total_runs=sum(s.run_count for s in summaries),
    )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceCostSummary)
async def get_workspace_detail(
    workspace_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
    session: Annotated[Session, Depends(get_session_dependency)],
    days_back: int = Query(default=30, ge=1, le=365),
):
    """Get detailed analytics for a single workspace.

    Requires SaaS owner role.
    """
    summary = analytics_service.get_single_workspace(session, workspace_id, days_back)

    if not summary:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return summary


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
    session: Annotated[Session, Depends(get_session_dependency)],
    days_back: int = Query(default=30, ge=1, le=365),
    workspace_id: Optional[UUID] = Query(default=None),
):
    """Get daily cost trend.

    Requires SaaS owner role.
    Optionally filter by workspace_id.
    """
    data = analytics_service.get_timeline(session, days_back, workspace_id)

    return TimelineResponse(data=data, days_back=days_back)


@router.get("/agents", response_model=AgentBreakdownResponse)
async def get_agent_breakdown(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
    session: Annotated[Session, Depends(get_session_dependency)],
    days_back: int = Query(default=30, ge=1, le=365),
    workspace_id: Optional[UUID] = Query(default=None),
):
    """Get cost breakdown by agent.

    Requires SaaS owner role.
    Optionally filter by workspace_id.
    """
    agents = analytics_service.get_agent_breakdown(session, days_back, workspace_id)

    return AgentBreakdownResponse(
        agents=agents,
        total_cost_usd=sum(a.total_cost_usd for a in agents),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_daily_costs(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
    session: Annotated[Session, Depends(get_session_dependency)],
    days_back: int = Query(default=30, ge=1, le=365),
    workspace_id: Optional[UUID] = Query(default=None),
):
    """Refresh daily cost rollups from workflow_runs.

    Requires SaaS owner role.
    Aggregates data from workflow_runs into workspace_daily_costs table.
    """
    records = analytics_service.refresh_daily_costs(session, days_back, workspace_id)

    return RefreshResponse(
        records_updated=records,
        message=f"Refreshed {records} daily cost records for the last {days_back} days",
    )
