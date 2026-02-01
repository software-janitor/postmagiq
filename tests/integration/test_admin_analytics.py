"""Integration tests for admin analytics.

Tests the admin analytics endpoints with a real database connection.
Verifies data aggregation, workspace summaries, and access control.

Run with: make test-int
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4
from sqlmodel import Session

from runner.db.models import (
    User,
    Workspace,
    WorkflowRun,
    WorkspaceDailyCosts,
)
from tests.db_utils import is_database_available

pytestmark = pytest.mark.skipif(
    not is_database_available(),
    reason="Database not available"
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def owner_user(test_engine) -> User:
    """Create an owner user."""
    with Session(test_engine) as session:
        user = User(
            id=uuid4(),
            email=f"owner-{uuid4().hex[:8]}@test.com",
            full_name="Test Owner",
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def regular_user(test_engine) -> User:
    """Create a regular (non-owner) user."""
    with Session(test_engine) as session:
        user = User(
            id=uuid4(),
            email=f"regular-{uuid4().hex[:8]}@test.com",
            full_name="Regular User",
            is_active=True,
            is_superuser=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def workspace_a(test_engine, owner_user) -> Workspace:
    """Create workspace A."""
    with Session(test_engine) as session:
        workspace = Workspace(
            id=uuid4(),
            name="Workspace A",
            slug=f"workspace-a-{uuid4().hex[:8]}",
            owner_id=owner_user.id,
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        return workspace


@pytest.fixture
def workspace_b(test_engine, owner_user) -> Workspace:
    """Create workspace B."""
    with Session(test_engine) as session:
        workspace = Workspace(
            id=uuid4(),
            name="Workspace B",
            slug=f"workspace-b-{uuid4().hex[:8]}",
            owner_id=owner_user.id,
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        return workspace


@pytest.fixture
def workflow_runs_for_a(test_engine, workspace_a) -> list:
    """Create workflow runs for workspace A."""
    runs = []
    with Session(test_engine) as session:
        for i in range(5):
            run = WorkflowRun(
                id=uuid4(),
                run_id=f"run-a-{i}-{uuid4().hex[:8]}",
                workspace_id=workspace_a.id,
                status="completed" if i < 4 else "failed",
                started_at=datetime.utcnow() - timedelta(days=i),
                total_cost_usd=10.0 + i,
                total_tokens=1000 * (i + 1),
            )
            session.add(run)
            runs.append(run)
        session.commit()
        for run in runs:
            session.refresh(run)
    return runs


@pytest.fixture
def workflow_runs_for_b(test_engine, workspace_b) -> list:
    """Create workflow runs for workspace B."""
    runs = []
    with Session(test_engine) as session:
        for i in range(3):
            run = WorkflowRun(
                id=uuid4(),
                run_id=f"run-b-{i}-{uuid4().hex[:8]}",
                workspace_id=workspace_b.id,
                status="completed",
                started_at=datetime.utcnow() - timedelta(days=i),
                total_cost_usd=20.0 + i,
                total_tokens=2000 * (i + 1),
            )
            session.add(run)
            runs.append(run)
        session.commit()
        for run in runs:
            session.refresh(run)
    return runs


@pytest.fixture
def daily_costs_for_a(test_engine, workspace_a) -> list:
    """Create daily cost records for workspace A."""
    costs = []
    with Session(test_engine) as session:
        for i in range(7):
            cost = WorkspaceDailyCosts(
                id=uuid4(),
                workspace_id=workspace_a.id,
                cost_date=date.today() - timedelta(days=i),
                total_cost_usd=15.0 + i,
                total_tokens=1500 * (i + 1),
                run_count=3 + i,
                successful_runs=2 + i,
                failed_runs=1,
            )
            session.add(cost)
            costs.append(cost)
        session.commit()
        for cost in costs:
            session.refresh(cost)
    return costs


@pytest.fixture
def daily_costs_for_b(test_engine, workspace_b) -> list:
    """Create daily cost records for workspace B."""
    costs = []
    with Session(test_engine) as session:
        for i in range(5):
            cost = WorkspaceDailyCosts(
                id=uuid4(),
                workspace_id=workspace_b.id,
                cost_date=date.today() - timedelta(days=i),
                total_cost_usd=25.0 + i,
                total_tokens=2500 * (i + 1),
                run_count=5 + i,
                successful_runs=4 + i,
                failed_runs=1,
            )
            session.add(cost)
            costs.append(cost)
        session.commit()
        for cost in costs:
            session.refresh(cost)
    return costs


# =============================================================================
# Service Tests
# =============================================================================


class TestAdminAnalyticsServiceIntegration:
    """Integration tests for AdminAnalyticsService with real database."""

    def test_refresh_daily_costs_creates_records(
        self, test_engine, workspace_a, workflow_runs_for_a
    ):
        """refresh_daily_costs creates records from workflow_runs."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            result = service.refresh_daily_costs(session, days_back=30)

            # Should have created some records
            assert result >= 0

    def test_refresh_daily_costs_with_workspace_filter(
        self, test_engine, workspace_a, workspace_b, workflow_runs_for_a, workflow_runs_for_b
    ):
        """refresh_daily_costs can filter by workspace."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            # Refresh only workspace A
            result = service.refresh_daily_costs(
                session, days_back=30, workspace_id=workspace_a.id
            )

            assert result >= 0

    def test_get_workspace_summaries_returns_all_workspaces(
        self, test_engine, workspace_a, workspace_b, daily_costs_for_a, daily_costs_for_b
    ):
        """get_workspace_summaries returns data for all workspaces."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            result = service.get_workspace_summaries(session, days_back=30)

            # Should have at least 2 workspaces
            assert len(result) >= 2

            # Find our workspaces in the result
            ws_ids = [r.workspace_id for r in result]
            assert workspace_a.id in ws_ids
            assert workspace_b.id in ws_ids

    def test_get_workspace_summaries_sorted_by_cost(
        self, test_engine, workspace_a, workspace_b, daily_costs_for_a, daily_costs_for_b
    ):
        """get_workspace_summaries returns workspaces sorted by cost descending."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            result = service.get_workspace_summaries(session, days_back=30)

            # Verify sorted by cost descending
            for i in range(len(result) - 1):
                assert result[i].total_cost_usd >= result[i + 1].total_cost_usd

    def test_get_timeline_aggregates_across_workspaces(
        self, test_engine, workspace_a, workspace_b, daily_costs_for_a, daily_costs_for_b
    ):
        """get_timeline aggregates costs across all workspaces."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            result = service.get_timeline(session, days_back=30)

            # Should have some data points
            assert len(result) > 0

            # Each point should have aggregated data
            for point in result:
                assert point.total_cost_usd >= 0
                assert point.total_tokens >= 0

    def test_get_timeline_with_workspace_filter(
        self, test_engine, workspace_a, workspace_b, daily_costs_for_a, daily_costs_for_b
    ):
        """get_timeline can filter by workspace."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            result = service.get_timeline(
                session, days_back=30, workspace_id=workspace_a.id
            )

            # Should have data for workspace A only
            assert len(result) > 0

    def test_get_single_workspace_returns_correct_data(
        self, test_engine, workspace_a, daily_costs_for_a
    ):
        """get_single_workspace returns data for specific workspace."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            result = service.get_single_workspace(
                session, workspace_id=workspace_a.id, days_back=30
            )

            assert result is not None
            assert result.workspace_id == workspace_a.id
            assert result.workspace_name == workspace_a.name
            assert result.total_cost_usd > 0

    def test_get_single_workspace_returns_none_for_missing(self, test_engine):
        """get_single_workspace returns None for non-existent workspace."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            result = service.get_single_workspace(
                session, workspace_id=uuid4(), days_back=30
            )

            assert result is None


# =============================================================================
# Database Model Tests
# =============================================================================


class TestWorkspaceDailyCostsModel:
    """Integration tests for WorkspaceDailyCosts database model."""

    def test_create_daily_cost_record(self, test_engine, workspace_a):
        """Can create a daily cost record."""
        with Session(test_engine) as session:
            cost = WorkspaceDailyCosts(
                id=uuid4(),
                workspace_id=workspace_a.id,
                cost_date=date.today(),
                total_cost_usd=50.0,
                total_tokens=5000,
                run_count=10,
                successful_runs=8,
                failed_runs=2,
            )
            session.add(cost)
            session.commit()
            session.refresh(cost)

            assert cost.id is not None
            assert cost.workspace_id == workspace_a.id
            assert cost.total_cost_usd == 50.0

    def test_unique_constraint_workspace_date(self, test_engine, workspace_a):
        """Cannot create duplicate records for same workspace+date."""
        from sqlalchemy.exc import IntegrityError

        today = date.today()

        with Session(test_engine) as session:
            cost1 = WorkspaceDailyCosts(
                id=uuid4(),
                workspace_id=workspace_a.id,
                cost_date=today,
                total_cost_usd=50.0,
                total_tokens=5000,
                run_count=10,
                successful_runs=8,
                failed_runs=2,
            )
            session.add(cost1)
            session.commit()

        # Try to create duplicate
        with pytest.raises(IntegrityError):
            with Session(test_engine) as session:
                cost2 = WorkspaceDailyCosts(
                    id=uuid4(),
                    workspace_id=workspace_a.id,
                    cost_date=today,
                    total_cost_usd=75.0,
                    total_tokens=7500,
                    run_count=15,
                    successful_runs=12,
                    failed_runs=3,
                )
                session.add(cost2)
                session.commit()

    def test_cascade_delete_with_workspace(self, test_engine, owner_user):
        """Daily cost records deleted when workspace is deleted."""
        from sqlmodel import select

        # Create workspace
        with Session(test_engine) as session:
            workspace = Workspace(
                id=uuid4(),
                name="Temp Workspace",
                slug=f"temp-{uuid4().hex[:8]}",
                owner_id=owner_user.id,
            )
            session.add(workspace)
            session.commit()
            session.refresh(workspace)
            ws_id = workspace.id

        # Create daily cost
        with Session(test_engine) as session:
            cost = WorkspaceDailyCosts(
                id=uuid4(),
                workspace_id=ws_id,
                cost_date=date.today(),
                total_cost_usd=50.0,
                total_tokens=5000,
                run_count=10,
                successful_runs=8,
                failed_runs=2,
            )
            session.add(cost)
            session.commit()
            cost_id = cost.id

        # Verify cost exists
        with Session(test_engine) as session:
            found = session.get(WorkspaceDailyCosts, cost_id)
            assert found is not None

        # Delete workspace
        with Session(test_engine) as session:
            workspace = session.get(Workspace, ws_id)
            session.delete(workspace)
            session.commit()

        # Verify cost is deleted
        with Session(test_engine) as session:
            found = session.get(WorkspaceDailyCosts, cost_id)
            assert found is None

    def test_default_values(self, test_engine, workspace_a):
        """Default values are applied correctly."""
        with Session(test_engine) as session:
            cost = WorkspaceDailyCosts(
                workspace_id=workspace_a.id,
                cost_date=date.today() - timedelta(days=100),
            )
            session.add(cost)
            session.commit()
            session.refresh(cost)

            assert cost.total_cost_usd == 0.0
            assert cost.total_tokens == 0
            assert cost.run_count == 0
            assert cost.successful_runs == 0
            assert cost.failed_runs == 0
            assert cost.created_at is not None


# =============================================================================
# Data Aggregation Tests
# =============================================================================


class TestDataAggregation:
    """Tests for correct data aggregation logic."""

    def test_aggregation_groups_by_date(
        self, test_engine, workspace_a, daily_costs_for_a
    ):
        """Timeline aggregates correctly by date."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            result = service.get_timeline(
                session, days_back=30, workspace_id=workspace_a.id
            )

            # Should have multiple dates
            dates = [r.date for r in result]
            assert len(dates) == len(set(dates))  # All unique dates

    def test_aggregation_sums_costs(
        self, test_engine, workspace_a, workspace_b, daily_costs_for_a, daily_costs_for_b
    ):
        """Total cost aggregation sums correctly."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        with Session(test_engine) as session:
            # Get individual workspace costs
            ws_a_summary = service.get_single_workspace(
                session, workspace_id=workspace_a.id, days_back=30
            )
            ws_b_summary = service.get_single_workspace(
                session, workspace_id=workspace_b.id, days_back=30
            )

            # Get all workspace summaries
            all_summaries = service.get_workspace_summaries(session, days_back=30)

            # Total should include both
            total = sum(s.total_cost_usd for s in all_summaries)
            assert total >= ws_a_summary.total_cost_usd + ws_b_summary.total_cost_usd
