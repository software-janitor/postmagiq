"""Service for admin analytics.

Provides aggregated metrics across all workspaces for SaaS owner.
On-demand aggregation from workflow_runs into workspace_daily_costs.
"""

from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from runner.db.engine import engine
from runner.db.models import (
    Workspace,
    WorkflowRun,
    WorkflowStateMetric,
    WorkspaceDailyCosts,
)


class WorkspaceCostSummary(BaseModel):
    """Cost summary for a single workspace."""

    workspace_id: UUID
    workspace_name: str
    total_cost_usd: float
    total_tokens: int
    run_count: int
    successful_runs: int
    failed_runs: int
    last_run_at: Optional[datetime]


class DailyCostPoint(BaseModel):
    """Single data point for timeline chart."""

    date: str  # ISO format YYYY-MM-DD
    total_cost_usd: float
    total_tokens: int
    run_count: int


class AgentCostBreakdown(BaseModel):
    """Cost breakdown by agent."""

    agent: str
    total_cost_usd: float
    total_tokens: int
    invocation_count: int


class AdminAnalyticsService:
    """Service for admin analytics operations."""

    def refresh_daily_costs(
        self,
        session: Session,
        days_back: int = 30,
        workspace_id: Optional[UUID] = None,
    ) -> int:
        """Aggregate workflow_runs into daily rollups.

        Args:
            session: Database session
            days_back: Number of days to backfill
            workspace_id: Optional filter for single workspace

        Returns:
            Number of records upserted
        """
        start_date = date.today() - timedelta(days=days_back)

        # Build query for workflow runs grouped by workspace and date
        query = (
            select(
                WorkflowRun.workspace_id,
                func.date(WorkflowRun.started_at).label("run_date"),
                func.sum(WorkflowRun.total_cost_usd).label("total_cost"),
                func.sum(WorkflowRun.total_tokens).label("total_tokens"),
                func.count(WorkflowRun.id).label("run_count"),
                func.sum(
                    func.cast(WorkflowRun.status == "completed", type_=func.INT)
                ).label("successful"),
                func.sum(
                    func.cast(WorkflowRun.status == "failed", type_=func.INT)
                ).label("failed"),
            )
            .where(WorkflowRun.workspace_id.is_not(None))
            .where(func.date(WorkflowRun.started_at) >= start_date)
            .group_by(WorkflowRun.workspace_id, func.date(WorkflowRun.started_at))
        )

        if workspace_id:
            query = query.where(WorkflowRun.workspace_id == workspace_id)

        results = session.exec(query).all()
        upserted = 0

        for row in results:
            ws_id = row.workspace_id
            run_date = row.run_date

            # Check for existing record
            existing = session.exec(
                select(WorkspaceDailyCosts).where(
                    WorkspaceDailyCosts.workspace_id == ws_id,
                    WorkspaceDailyCosts.cost_date == run_date,
                )
            ).first()

            if existing:
                # Update existing
                existing.total_cost_usd = row.total_cost or 0.0
                existing.total_tokens = row.total_tokens or 0
                existing.run_count = row.run_count or 0
                existing.successful_runs = row.successful or 0
                existing.failed_runs = row.failed or 0
                existing.updated_at = datetime.utcnow()
                session.add(existing)
            else:
                # Create new
                new_record = WorkspaceDailyCosts(
                    workspace_id=ws_id,
                    cost_date=run_date,
                    total_cost_usd=row.total_cost or 0.0,
                    total_tokens=row.total_tokens or 0,
                    run_count=row.run_count or 0,
                    successful_runs=row.successful or 0,
                    failed_runs=row.failed or 0,
                )
                session.add(new_record)

            upserted += 1

        session.commit()
        return upserted

    def get_workspace_summaries(
        self,
        session: Session,
        days_back: int = 30,
    ) -> list[WorkspaceCostSummary]:
        """Get cost summary for all workspaces.

        Args:
            session: Database session
            days_back: Number of days to include

        Returns:
            List of workspace cost summaries
        """
        start_date = date.today() - timedelta(days=days_back)

        # Query daily costs aggregated by workspace
        cost_query = (
            select(
                WorkspaceDailyCosts.workspace_id,
                func.sum(WorkspaceDailyCosts.total_cost_usd).label("total_cost"),
                func.sum(WorkspaceDailyCosts.total_tokens).label("total_tokens"),
                func.sum(WorkspaceDailyCosts.run_count).label("run_count"),
                func.sum(WorkspaceDailyCosts.successful_runs).label("successful"),
                func.sum(WorkspaceDailyCosts.failed_runs).label("failed"),
            )
            .where(WorkspaceDailyCosts.cost_date >= start_date)
            .group_by(WorkspaceDailyCosts.workspace_id)
        )

        cost_results = {r.workspace_id: r for r in session.exec(cost_query).all()}

        # Get last run for each workspace
        last_run_query = (
            select(
                WorkflowRun.workspace_id,
                func.max(WorkflowRun.started_at).label("last_run"),
            )
            .where(WorkflowRun.workspace_id.is_not(None))
            .group_by(WorkflowRun.workspace_id)
        )
        last_runs = {r.workspace_id: r.last_run for r in session.exec(last_run_query).all()}

        # Get all workspaces
        workspaces = session.exec(select(Workspace)).all()

        summaries = []
        for ws in workspaces:
            cost_data = cost_results.get(ws.id)
            summaries.append(
                WorkspaceCostSummary(
                    workspace_id=ws.id,
                    workspace_name=ws.name,
                    total_cost_usd=cost_data.total_cost if cost_data else 0.0,
                    total_tokens=cost_data.total_tokens if cost_data else 0,
                    run_count=cost_data.run_count if cost_data else 0,
                    successful_runs=cost_data.successful if cost_data else 0,
                    failed_runs=cost_data.failed if cost_data else 0,
                    last_run_at=last_runs.get(ws.id),
                )
            )

        # Sort by cost descending
        summaries.sort(key=lambda s: s.total_cost_usd, reverse=True)
        return summaries

    def get_timeline(
        self,
        session: Session,
        days_back: int = 30,
        workspace_id: Optional[UUID] = None,
    ) -> list[DailyCostPoint]:
        """Get daily cost trend.

        Args:
            session: Database session
            days_back: Number of days to include
            workspace_id: Optional filter for single workspace

        Returns:
            List of daily cost points
        """
        start_date = date.today() - timedelta(days=days_back)

        query = (
            select(
                WorkspaceDailyCosts.cost_date,
                func.sum(WorkspaceDailyCosts.total_cost_usd).label("total_cost"),
                func.sum(WorkspaceDailyCosts.total_tokens).label("total_tokens"),
                func.sum(WorkspaceDailyCosts.run_count).label("run_count"),
            )
            .where(WorkspaceDailyCosts.cost_date >= start_date)
            .group_by(WorkspaceDailyCosts.cost_date)
            .order_by(WorkspaceDailyCosts.cost_date)
        )

        if workspace_id:
            query = query.where(WorkspaceDailyCosts.workspace_id == workspace_id)

        results = session.exec(query).all()

        return [
            DailyCostPoint(
                date=r.cost_date.isoformat(),
                total_cost_usd=r.total_cost or 0.0,
                total_tokens=r.total_tokens or 0,
                run_count=r.run_count or 0,
            )
            for r in results
        ]

    def get_agent_breakdown(
        self,
        session: Session,
        days_back: int = 30,
        workspace_id: Optional[UUID] = None,
    ) -> list[AgentCostBreakdown]:
        """Get cost breakdown by agent.

        Args:
            session: Database session
            days_back: Number of days to include
            workspace_id: Optional filter for single workspace

        Returns:
            List of agent cost breakdowns
        """
        start_date = datetime.utcnow() - timedelta(days=days_back)

        # Join WorkflowStateMetric with WorkflowRun for workspace filtering
        query = (
            select(
                WorkflowStateMetric.agent,
                func.sum(WorkflowStateMetric.cost_usd).label("total_cost"),
                func.sum(
                    WorkflowStateMetric.tokens_input + WorkflowStateMetric.tokens_output
                ).label("total_tokens"),
                func.count(WorkflowStateMetric.id).label("invocation_count"),
            )
            .join(WorkflowRun, WorkflowStateMetric.run_id == WorkflowRun.run_id)
            .where(WorkflowStateMetric.created_at >= start_date)
            .group_by(WorkflowStateMetric.agent)
            .order_by(func.sum(WorkflowStateMetric.cost_usd).desc())
        )

        if workspace_id:
            query = query.where(WorkflowRun.workspace_id == workspace_id)

        results = session.exec(query).all()

        return [
            AgentCostBreakdown(
                agent=r.agent,
                total_cost_usd=r.total_cost or 0.0,
                total_tokens=r.total_tokens or 0,
                invocation_count=r.invocation_count or 0,
            )
            for r in results
        ]

    def get_single_workspace(
        self,
        session: Session,
        workspace_id: UUID,
        days_back: int = 30,
    ) -> Optional[WorkspaceCostSummary]:
        """Get detailed analytics for a single workspace.

        Args:
            session: Database session
            workspace_id: Workspace UUID
            days_back: Number of days to include

        Returns:
            Workspace cost summary or None if not found
        """
        workspace = session.get(Workspace, workspace_id)
        if not workspace:
            return None

        start_date = date.today() - timedelta(days=days_back)

        # Aggregate daily costs
        cost_query = (
            select(
                func.sum(WorkspaceDailyCosts.total_cost_usd).label("total_cost"),
                func.sum(WorkspaceDailyCosts.total_tokens).label("total_tokens"),
                func.sum(WorkspaceDailyCosts.run_count).label("run_count"),
                func.sum(WorkspaceDailyCosts.successful_runs).label("successful"),
                func.sum(WorkspaceDailyCosts.failed_runs).label("failed"),
            )
            .where(WorkspaceDailyCosts.workspace_id == workspace_id)
            .where(WorkspaceDailyCosts.cost_date >= start_date)
        )

        cost_result = session.exec(cost_query).first()

        # Get last run
        last_run_query = (
            select(func.max(WorkflowRun.started_at))
            .where(WorkflowRun.workspace_id == workspace_id)
        )
        last_run = session.exec(last_run_query).first()

        return WorkspaceCostSummary(
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            total_cost_usd=cost_result.total_cost if cost_result and cost_result.total_cost else 0.0,
            total_tokens=cost_result.total_tokens if cost_result and cost_result.total_tokens else 0,
            run_count=cost_result.run_count if cost_result and cost_result.run_count else 0,
            successful_runs=cost_result.successful if cost_result and cost_result.successful else 0,
            failed_runs=cost_result.failed if cost_result and cost_result.failed else 0,
            last_run_at=last_run,
        )
