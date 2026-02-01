"""Tests for admin analytics service.

Tests aggregation logic, workspace summaries, timeline, and agent breakdown.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4


class TestAdminAnalyticsServiceImport:
    """Tests for AdminAnalyticsService import."""

    def test_service_can_be_imported(self):
        """AdminAnalyticsService can be imported."""
        from api.services.admin_analytics_service import (
            AdminAnalyticsService,
            WorkspaceCostSummary,
            DailyCostPoint,
            AgentCostBreakdown,
        )

        assert AdminAnalyticsService is not None
        assert WorkspaceCostSummary is not None
        assert DailyCostPoint is not None
        assert AgentCostBreakdown is not None

    def test_service_instantiation(self):
        """AdminAnalyticsService can be instantiated."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        assert service is not None


class TestWorkspaceCostSummaryModel:
    """Tests for WorkspaceCostSummary Pydantic model."""

    def test_workspace_cost_summary_creation(self):
        """WorkspaceCostSummary can be created with valid data."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        summary = WorkspaceCostSummary(
            workspace_id=uuid4(),
            workspace_name="Test Workspace",
            total_cost_usd=123.45,
            total_tokens=50000,
            run_count=10,
            successful_runs=8,
            failed_runs=2,
            last_run_at=datetime.utcnow(),
        )

        assert summary.workspace_name == "Test Workspace"
        assert summary.total_cost_usd == 123.45
        assert summary.total_tokens == 50000
        assert summary.run_count == 10

    def test_workspace_cost_summary_nullable_last_run(self):
        """WorkspaceCostSummary allows null last_run_at."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        summary = WorkspaceCostSummary(
            workspace_id=uuid4(),
            workspace_name="New Workspace",
            total_cost_usd=0.0,
            total_tokens=0,
            run_count=0,
            successful_runs=0,
            failed_runs=0,
            last_run_at=None,
        )

        assert summary.last_run_at is None

    def test_workspace_cost_summary_serialization(self):
        """WorkspaceCostSummary serializes correctly."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        ws_id = uuid4()
        summary = WorkspaceCostSummary(
            workspace_id=ws_id,
            workspace_name="Test",
            total_cost_usd=10.5,
            total_tokens=1000,
            run_count=5,
            successful_runs=4,
            failed_runs=1,
            last_run_at=None,
        )

        data = summary.model_dump()
        assert data["workspace_id"] == ws_id
        assert data["total_cost_usd"] == 10.5
        assert "workspace_name" in data

    def test_workspace_cost_summary_zero_values(self):
        """WorkspaceCostSummary handles zero values correctly."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        summary = WorkspaceCostSummary(
            workspace_id=uuid4(),
            workspace_name="Empty",
            total_cost_usd=0.0,
            total_tokens=0,
            run_count=0,
            successful_runs=0,
            failed_runs=0,
            last_run_at=None,
        )

        assert summary.total_cost_usd == 0.0
        assert summary.total_tokens == 0
        assert summary.run_count == 0


class TestDailyCostPointModel:
    """Tests for DailyCostPoint Pydantic model."""

    def test_daily_cost_point_creation(self):
        """DailyCostPoint can be created with valid data."""
        from api.services.admin_analytics_service import DailyCostPoint

        point = DailyCostPoint(
            date="2026-01-31",
            total_cost_usd=50.25,
            total_tokens=25000,
            run_count=5,
        )

        assert point.date == "2026-01-31"
        assert point.total_cost_usd == 50.25
        assert point.total_tokens == 25000
        assert point.run_count == 5

    def test_daily_cost_point_serialization(self):
        """DailyCostPoint serializes to dict correctly."""
        from api.services.admin_analytics_service import DailyCostPoint

        point = DailyCostPoint(
            date="2026-01-30",
            total_cost_usd=100.0,
            total_tokens=50000,
            run_count=10,
        )

        data = point.model_dump()
        assert data["date"] == "2026-01-30"
        assert data["total_cost_usd"] == 100.0

    def test_daily_cost_point_zero_values(self):
        """DailyCostPoint handles zero values."""
        from api.services.admin_analytics_service import DailyCostPoint

        point = DailyCostPoint(
            date="2026-01-01",
            total_cost_usd=0.0,
            total_tokens=0,
            run_count=0,
        )

        assert point.total_cost_usd == 0.0
        assert point.run_count == 0


class TestAgentCostBreakdownModel:
    """Tests for AgentCostBreakdown Pydantic model."""

    def test_agent_cost_breakdown_creation(self):
        """AgentCostBreakdown can be created with valid data."""
        from api.services.admin_analytics_service import AgentCostBreakdown

        breakdown = AgentCostBreakdown(
            agent="claude",
            total_cost_usd=75.50,
            total_tokens=100000,
            invocation_count=50,
        )

        assert breakdown.agent == "claude"
        assert breakdown.total_cost_usd == 75.50
        assert breakdown.total_tokens == 100000
        assert breakdown.invocation_count == 50

    def test_agent_cost_breakdown_different_agents(self):
        """AgentCostBreakdown works with different agent names."""
        from api.services.admin_analytics_service import AgentCostBreakdown

        agents = ["claude", "gemini", "gpt-4", "custom-agent"]
        for agent_name in agents:
            breakdown = AgentCostBreakdown(
                agent=agent_name,
                total_cost_usd=10.0,
                total_tokens=1000,
                invocation_count=5,
            )
            assert breakdown.agent == agent_name

    def test_agent_cost_breakdown_serialization(self):
        """AgentCostBreakdown serializes correctly."""
        from api.services.admin_analytics_service import AgentCostBreakdown

        breakdown = AgentCostBreakdown(
            agent="test-agent",
            total_cost_usd=25.0,
            total_tokens=5000,
            invocation_count=10,
        )

        data = breakdown.model_dump()
        assert data["agent"] == "test-agent"
        assert data["invocation_count"] == 10


class TestRefreshDailyCosts:
    """Tests for refresh_daily_costs method."""

    def test_service_has_refresh_method(self):
        """AdminAnalyticsService has refresh_daily_costs method."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        assert hasattr(service, "refresh_daily_costs")
        assert callable(service.refresh_daily_costs)

    def test_refresh_returns_count_with_empty_data(self):
        """refresh_daily_costs returns 0 when no data exists."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []

        result = service.refresh_daily_costs(mock_session, days_back=30)

        assert result == 0
        mock_session.commit.assert_called_once()

    def test_refresh_with_workspace_filter(self):
        """refresh_daily_costs accepts workspace_id filter."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []

        workspace_id = uuid4()
        result = service.refresh_daily_costs(
            mock_session, days_back=7, workspace_id=workspace_id
        )

        assert result == 0

    def test_refresh_creates_new_records(self):
        """refresh_daily_costs creates new records when none exist."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        # Create mock row result
        mock_row = MagicMock()
        mock_row.workspace_id = uuid4()
        mock_row.run_date = date.today()
        mock_row.total_cost = 10.5
        mock_row.total_tokens = 1000
        mock_row.run_count = 5
        mock_row.successful = 4
        mock_row.failed = 1

        # First exec returns the aggregated data
        # Second exec (for existing check) returns None
        mock_session.exec.return_value.all.return_value = [mock_row]
        mock_session.exec.return_value.first.return_value = None

        result = service.refresh_daily_costs(mock_session, days_back=30)

        assert result == 1
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

    def test_refresh_updates_existing_records(self):
        """refresh_daily_costs updates existing records."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        ws_id = uuid4()

        # Mock aggregated data
        mock_row = MagicMock()
        mock_row.workspace_id = ws_id
        mock_row.run_date = date.today()
        mock_row.total_cost = 20.0
        mock_row.total_tokens = 2000
        mock_row.run_count = 10
        mock_row.successful = 8
        mock_row.failed = 2

        # Mock existing record
        mock_existing = MagicMock()
        mock_existing.workspace_id = ws_id
        mock_existing.total_cost_usd = 10.0

        mock_session.exec.return_value.all.return_value = [mock_row]
        mock_session.exec.return_value.first.return_value = mock_existing

        result = service.refresh_daily_costs(mock_session, days_back=30)

        assert result == 1
        # Verify existing record was updated
        assert mock_existing.total_cost_usd == 20.0
        assert mock_existing.total_tokens == 2000


class TestGetWorkspaceSummaries:
    """Tests for get_workspace_summaries method."""

    def test_returns_list(self):
        """get_workspace_summaries returns a list."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        # Mock empty results for both queries
        mock_session.exec.return_value.all.return_value = []

        result = service.get_workspace_summaries(mock_session, days_back=30)

        assert isinstance(result, list)

    def test_returns_empty_list_for_no_workspaces(self):
        """get_workspace_summaries returns empty list when no workspaces."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []

        result = service.get_workspace_summaries(mock_session, days_back=30)

        assert result == []

    def test_returns_summary_for_workspace(self):
        """get_workspace_summaries returns summary for each workspace."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        ws_id = uuid4()

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.id = ws_id
        mock_workspace.name = "Test Workspace"

        # Mock cost data
        mock_cost = MagicMock()
        mock_cost.workspace_id = ws_id
        mock_cost.total_cost = 100.0
        mock_cost.total_tokens = 10000
        mock_cost.run_count = 20
        mock_cost.successful = 18
        mock_cost.failed = 2

        # Configure mock returns
        def exec_side_effect(query):
            result = MagicMock()
            result.all.return_value = [mock_cost]
            return result

        mock_session.exec.side_effect = exec_side_effect

        # Third call returns workspaces
        original_side_effect = mock_session.exec.side_effect
        call_count = [0]

        def exec_with_workspaces(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] <= 2:
                result.all.return_value = [mock_cost]
            else:
                result.all.return_value = [mock_workspace]
            return result

        mock_session.exec.side_effect = exec_with_workspaces

        result = service.get_workspace_summaries(mock_session, days_back=30)

        assert isinstance(result, list)

    def test_summaries_sorted_by_cost_descending(self):
        """get_workspace_summaries sorts by cost descending."""
        from api.services.admin_analytics_service import (
            AdminAnalyticsService,
            WorkspaceCostSummary,
        )

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        # Create workspaces with different costs
        ws1_id = uuid4()
        ws2_id = uuid4()

        mock_ws1 = MagicMock()
        mock_ws1.id = ws1_id
        mock_ws1.name = "Low Cost Workspace"

        mock_ws2 = MagicMock()
        mock_ws2.id = ws2_id
        mock_ws2.name = "High Cost Workspace"

        # Mock cost data
        mock_cost1 = MagicMock()
        mock_cost1.workspace_id = ws1_id
        mock_cost1.total_cost = 10.0
        mock_cost1.total_tokens = 1000
        mock_cost1.run_count = 5
        mock_cost1.successful = 5
        mock_cost1.failed = 0

        mock_cost2 = MagicMock()
        mock_cost2.workspace_id = ws2_id
        mock_cost2.total_cost = 100.0
        mock_cost2.total_tokens = 10000
        mock_cost2.run_count = 50
        mock_cost2.successful = 48
        mock_cost2.failed = 2

        call_count = [0]

        def exec_with_data(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # Cost query
                result.all.return_value = [mock_cost1, mock_cost2]
            elif call_count[0] == 2:
                # Last run query
                result.all.return_value = []
            else:
                # Workspaces query
                result.all.return_value = [mock_ws1, mock_ws2]
            return result

        mock_session.exec.side_effect = exec_with_data

        result = service.get_workspace_summaries(mock_session, days_back=30)

        assert len(result) == 2
        # Higher cost should be first
        assert result[0].total_cost_usd >= result[1].total_cost_usd


class TestGetTimeline:
    """Tests for get_timeline method."""

    def test_returns_list(self):
        """get_timeline returns a list of DailyCostPoints."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        # Mock empty results
        mock_session.exec.return_value.all.return_value = []

        result = service.get_timeline(mock_session, days_back=30)

        assert isinstance(result, list)

    def test_returns_daily_cost_points(self):
        """get_timeline returns DailyCostPoint objects."""
        from api.services.admin_analytics_service import (
            AdminAnalyticsService,
            DailyCostPoint,
        )

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        # Mock timeline data
        mock_point = MagicMock()
        mock_point.cost_date = date(2026, 1, 31)
        mock_point.total_cost = 50.0
        mock_point.total_tokens = 5000
        mock_point.run_count = 10

        mock_session.exec.return_value.all.return_value = [mock_point]

        result = service.get_timeline(mock_session, days_back=30)

        assert len(result) == 1
        assert isinstance(result[0], DailyCostPoint)
        assert result[0].date == "2026-01-31"
        assert result[0].total_cost_usd == 50.0

    def test_timeline_with_workspace_filter(self):
        """get_timeline accepts workspace_id filter."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []

        workspace_id = uuid4()
        result = service.get_timeline(
            mock_session, days_back=7, workspace_id=workspace_id
        )

        assert isinstance(result, list)

    def test_timeline_handles_null_values(self):
        """get_timeline handles null values gracefully."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        mock_point = MagicMock()
        mock_point.cost_date = date(2026, 1, 30)
        mock_point.total_cost = None
        mock_point.total_tokens = None
        mock_point.run_count = None

        mock_session.exec.return_value.all.return_value = [mock_point]

        result = service.get_timeline(mock_session, days_back=30)

        assert len(result) == 1
        assert result[0].total_cost_usd == 0.0
        assert result[0].total_tokens == 0
        assert result[0].run_count == 0


class TestGetAgentBreakdown:
    """Tests for get_agent_breakdown method."""

    def test_returns_list(self):
        """get_agent_breakdown returns a list of AgentCostBreakdowns."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        # Mock empty results
        mock_session.exec.return_value.all.return_value = []

        result = service.get_agent_breakdown(mock_session, days_back=30)

        assert isinstance(result, list)

    def test_returns_agent_cost_breakdowns(self):
        """get_agent_breakdown returns AgentCostBreakdown objects."""
        from api.services.admin_analytics_service import (
            AdminAnalyticsService,
            AgentCostBreakdown,
        )

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        mock_agent = MagicMock()
        mock_agent.agent = "claude"
        mock_agent.total_cost = 75.0
        mock_agent.total_tokens = 10000
        mock_agent.invocation_count = 25

        mock_session.exec.return_value.all.return_value = [mock_agent]

        result = service.get_agent_breakdown(mock_session, days_back=30)

        assert len(result) == 1
        assert isinstance(result[0], AgentCostBreakdown)
        assert result[0].agent == "claude"
        assert result[0].total_cost_usd == 75.0

    def test_agent_breakdown_with_workspace_filter(self):
        """get_agent_breakdown accepts workspace_id filter."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []

        workspace_id = uuid4()
        result = service.get_agent_breakdown(
            mock_session, days_back=7, workspace_id=workspace_id
        )

        assert isinstance(result, list)

    def test_agent_breakdown_handles_null_values(self):
        """get_agent_breakdown handles null values gracefully."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        mock_agent = MagicMock()
        mock_agent.agent = "test"
        mock_agent.total_cost = None
        mock_agent.total_tokens = None
        mock_agent.invocation_count = None

        mock_session.exec.return_value.all.return_value = [mock_agent]

        result = service.get_agent_breakdown(mock_session, days_back=30)

        assert len(result) == 1
        assert result[0].total_cost_usd == 0.0
        assert result[0].total_tokens == 0
        assert result[0].invocation_count == 0

    def test_multiple_agents(self):
        """get_agent_breakdown returns multiple agents."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        mock_agents = []
        for name in ["claude", "gemini", "gpt-4"]:
            mock_agent = MagicMock()
            mock_agent.agent = name
            mock_agent.total_cost = 50.0
            mock_agent.total_tokens = 5000
            mock_agent.invocation_count = 10
            mock_agents.append(mock_agent)

        mock_session.exec.return_value.all.return_value = mock_agents

        result = service.get_agent_breakdown(mock_session, days_back=30)

        assert len(result) == 3
        agent_names = [r.agent for r in result]
        assert "claude" in agent_names
        assert "gemini" in agent_names
        assert "gpt-4" in agent_names


class TestGetSingleWorkspace:
    """Tests for get_single_workspace method."""

    def test_returns_none_for_missing_workspace(self):
        """get_single_workspace returns None if workspace not found."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        # Mock workspace not found
        mock_session.get.return_value = None

        result = service.get_single_workspace(
            mock_session,
            workspace_id=uuid4(),
            days_back=30,
        )

        assert result is None

    def test_returns_workspace_summary(self):
        """get_single_workspace returns WorkspaceCostSummary."""
        from api.services.admin_analytics_service import (
            AdminAnalyticsService,
            WorkspaceCostSummary,
        )

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        ws_id = uuid4()

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.id = ws_id
        mock_workspace.name = "Test Workspace"

        mock_session.get.return_value = mock_workspace

        # Mock cost data
        mock_cost = MagicMock()
        mock_cost.total_cost = 100.0
        mock_cost.total_tokens = 10000
        mock_cost.run_count = 20
        mock_cost.successful = 18
        mock_cost.failed = 2

        mock_session.exec.return_value.first.return_value = mock_cost

        result = service.get_single_workspace(mock_session, workspace_id=ws_id)

        assert result is not None
        assert isinstance(result, WorkspaceCostSummary)
        assert result.workspace_id == ws_id
        assert result.workspace_name == "Test Workspace"
        assert result.total_cost_usd == 100.0

    def test_handles_null_cost_data(self):
        """get_single_workspace handles null cost data."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        mock_session = MagicMock()

        ws_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.id = ws_id
        mock_workspace.name = "Empty Workspace"

        mock_session.get.return_value = mock_workspace

        # No cost data
        mock_cost = MagicMock()
        mock_cost.total_cost = None
        mock_cost.total_tokens = None
        mock_cost.run_count = None
        mock_cost.successful = None
        mock_cost.failed = None

        mock_session.exec.return_value.first.return_value = mock_cost

        result = service.get_single_workspace(mock_session, workspace_id=ws_id)

        assert result is not None
        assert result.total_cost_usd == 0.0
        assert result.total_tokens == 0


class TestDatabaseModel:
    """Tests for WorkspaceDailyCosts database model."""

    def test_model_can_be_imported(self):
        """WorkspaceDailyCosts model can be imported."""
        from runner.db.models import (
            WorkspaceDailyCosts,
            WorkspaceDailyCostsCreate,
            WorkspaceDailyCostsRead,
        )

        assert WorkspaceDailyCosts is not None
        assert WorkspaceDailyCostsCreate is not None
        assert WorkspaceDailyCostsRead is not None

    def test_model_has_correct_table_name(self):
        """WorkspaceDailyCosts has correct table name."""
        from runner.db.models import WorkspaceDailyCosts

        assert WorkspaceDailyCosts.__tablename__ == "workspace_daily_costs"

    def test_model_has_required_fields(self):
        """WorkspaceDailyCosts has all required fields."""
        from runner.db.models import WorkspaceDailyCosts

        # Check field names exist in model
        fields = WorkspaceDailyCosts.model_fields
        required_fields = [
            "id",
            "workspace_id",
            "cost_date",
            "total_cost_usd",
            "total_tokens",
            "run_count",
            "successful_runs",
            "failed_runs",
            "created_at",
        ]

        for field in required_fields:
            assert field in fields, f"Missing field: {field}"

    def test_create_model_fields(self):
        """WorkspaceDailyCostsCreate has correct fields."""
        from runner.db.models import WorkspaceDailyCostsCreate

        fields = WorkspaceDailyCostsCreate.model_fields
        assert "workspace_id" in fields
        assert "cost_date" in fields
        assert "total_cost_usd" in fields

    def test_read_model_fields(self):
        """WorkspaceDailyCostsRead has correct fields."""
        from runner.db.models import WorkspaceDailyCostsRead

        fields = WorkspaceDailyCostsRead.model_fields
        assert "id" in fields
        assert "workspace_id" in fields
        assert "cost_date" in fields
        assert "created_at" in fields
