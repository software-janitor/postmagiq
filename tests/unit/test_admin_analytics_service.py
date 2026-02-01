"""Tests for admin analytics service.

Tests aggregation logic, workspace summaries, timeline, and agent breakdown.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
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


class TestRefreshDailyCosts:
    """Tests for refresh_daily_costs method."""

    def test_service_has_refresh_method(self):
        """AdminAnalyticsService has refresh_daily_costs method."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        assert hasattr(service, "refresh_daily_costs")
        assert callable(service.refresh_daily_costs)


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
