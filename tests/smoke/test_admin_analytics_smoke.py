"""Smoke tests for admin analytics.

These tests verify basic functionality without making real API calls or using a database.
Run with: pytest tests/smoke/test_admin_analytics_smoke.py -v
"""

import pytest
from datetime import date, datetime
from uuid import uuid4


class TestAdminAnalyticsServiceSmoke:
    """Basic smoke tests for admin analytics service."""

    def test_service_can_be_imported(self):
        """AdminAnalyticsService can be imported."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        assert AdminAnalyticsService is not None

    def test_service_can_be_instantiated(self):
        """AdminAnalyticsService can be instantiated without errors."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()
        assert service is not None

    def test_service_has_required_methods(self):
        """AdminAnalyticsService has all expected methods."""
        from api.services.admin_analytics_service import AdminAnalyticsService

        service = AdminAnalyticsService()

        required_methods = [
            "refresh_daily_costs",
            "get_workspace_summaries",
            "get_timeline",
            "get_agent_breakdown",
            "get_single_workspace",
        ]

        for method in required_methods:
            assert hasattr(service, method), f"Missing method: {method}"
            assert callable(getattr(service, method)), f"Not callable: {method}"


class TestAdminAnalyticsModelsSmoke:
    """Smoke tests for admin analytics Pydantic models."""

    def test_workspace_cost_summary_model(self):
        """WorkspaceCostSummary model can be created."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        summary = WorkspaceCostSummary(
            workspace_id=uuid4(),
            workspace_name="Test",
            total_cost_usd=100.0,
            total_tokens=10000,
            run_count=20,
            successful_runs=18,
            failed_runs=2,
            last_run_at=None,
        )

        assert summary.workspace_name == "Test"
        assert summary.total_cost_usd == 100.0

    def test_daily_cost_point_model(self):
        """DailyCostPoint model can be created."""
        from api.services.admin_analytics_service import DailyCostPoint

        point = DailyCostPoint(
            date="2026-01-31",
            total_cost_usd=50.0,
            total_tokens=5000,
            run_count=10,
        )

        assert point.date == "2026-01-31"
        assert point.total_cost_usd == 50.0

    def test_agent_cost_breakdown_model(self):
        """AgentCostBreakdown model can be created."""
        from api.services.admin_analytics_service import AgentCostBreakdown

        breakdown = AgentCostBreakdown(
            agent="claude",
            total_cost_usd=75.0,
            total_tokens=10000,
            invocation_count=25,
        )

        assert breakdown.agent == "claude"
        assert breakdown.invocation_count == 25


class TestAdminRoutesSmoke:
    """Smoke tests for admin routes module."""

    def test_router_can_be_imported(self):
        """Admin router can be imported."""
        from api.routes.v1.admin import router

        assert router is not None

    def test_router_has_correct_prefix(self):
        """Router has expected prefix."""
        from api.routes.v1.admin import router

        assert router.prefix == "/v1/admin/analytics"

    def test_router_has_correct_tags(self):
        """Router has expected tags."""
        from api.routes.v1.admin import router

        assert "admin-analytics" in router.tags

    def test_response_models_can_be_imported(self):
        """Response models can be imported."""
        from api.routes.v1.admin import (
            WorkspaceSummariesResponse,
            TimelineResponse,
            AgentBreakdownResponse,
            RefreshResponse,
        )

        assert WorkspaceSummariesResponse is not None
        assert TimelineResponse is not None
        assert AgentBreakdownResponse is not None
        assert RefreshResponse is not None

    def test_service_instance_available(self):
        """Analytics service instance is available in routes module."""
        from api.routes.v1.admin import analytics_service
        from api.services.admin_analytics_service import AdminAnalyticsService

        assert isinstance(analytics_service, AdminAnalyticsService)


class TestAdminRouteResponseModelsSmoke:
    """Smoke tests for route response models."""

    def test_workspaces_summaries_response_creation(self):
        """WorkspaceSummariesResponse can be created."""
        from api.routes.v1.admin import WorkspaceSummariesResponse

        response = WorkspaceSummariesResponse(
            workspaces=[],
            total_cost_usd=0.0,
            total_tokens=0,
            total_runs=0,
        )

        assert response.workspaces == []
        assert response.total_cost_usd == 0.0

    def test_timeline_response_creation(self):
        """TimelineResponse can be created."""
        from api.routes.v1.admin import TimelineResponse

        response = TimelineResponse(
            data=[],
            days_back=30,
        )

        assert response.data == []
        assert response.days_back == 30

    def test_agent_breakdown_response_creation(self):
        """AgentBreakdownResponse can be created."""
        from api.routes.v1.admin import AgentBreakdownResponse

        response = AgentBreakdownResponse(
            agents=[],
            total_cost_usd=0.0,
        )

        assert response.agents == []
        assert response.total_cost_usd == 0.0

    def test_refresh_response_creation(self):
        """RefreshResponse can be created."""
        from api.routes.v1.admin import RefreshResponse

        response = RefreshResponse(
            records_updated=42,
            message="Test message",
        )

        assert response.records_updated == 42
        assert response.message == "Test message"


class TestDatabaseModelSmoke:
    """Smoke tests for database models."""

    def test_workspace_daily_costs_model_import(self):
        """WorkspaceDailyCosts model can be imported."""
        from runner.db.models import (
            WorkspaceDailyCosts,
            WorkspaceDailyCostsCreate,
            WorkspaceDailyCostsRead,
        )

        assert WorkspaceDailyCosts is not None
        assert WorkspaceDailyCostsCreate is not None
        assert WorkspaceDailyCostsRead is not None

    def test_workspace_daily_costs_table_name(self):
        """WorkspaceDailyCosts has correct table name."""
        from runner.db.models import WorkspaceDailyCosts

        assert WorkspaceDailyCosts.__tablename__ == "workspace_daily_costs"

    def test_workspace_daily_costs_fields(self):
        """WorkspaceDailyCosts has expected fields."""
        from runner.db.models import WorkspaceDailyCosts

        fields = WorkspaceDailyCosts.model_fields

        expected = [
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

        for field in expected:
            assert field in fields, f"Missing field: {field}"


class TestRouteDefinitionsSmoke:
    """Smoke tests for route definitions."""

    def test_routes_exist(self):
        """Expected routes are defined."""
        from api.routes.v1.admin import router

        routes = [r.path for r in router.routes]

        expected_patterns = [
            "workspaces",
            "timeline",
            "agents",
            "refresh",
        ]

        for pattern in expected_patterns:
            assert any(
                pattern in r for r in routes
            ), f"Missing route pattern: {pattern}"

    def test_route_methods_correct(self):
        """Routes use correct HTTP methods."""
        from api.routes.v1.admin import router

        for route in router.routes:
            if not hasattr(route, "path"):
                continue

            if "refresh" in route.path:
                assert "POST" in route.methods, "refresh should be POST"
            elif any(x in route.path for x in ["workspaces", "timeline", "agents"]):
                assert "GET" in route.methods, f"{route.path} should be GET"


class TestModelSerializationSmoke:
    """Smoke tests for model serialization."""

    def test_workspace_cost_summary_serialization(self):
        """WorkspaceCostSummary serializes to JSON-compatible dict."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        ws_id = uuid4()
        summary = WorkspaceCostSummary(
            workspace_id=ws_id,
            workspace_name="Test",
            total_cost_usd=100.0,
            total_tokens=10000,
            run_count=20,
            successful_runs=18,
            failed_runs=2,
            last_run_at=datetime.utcnow(),
        )

        data = summary.model_dump()

        assert "workspace_id" in data
        assert "workspace_name" in data
        assert "total_cost_usd" in data
        assert data["workspace_name"] == "Test"

    def test_daily_cost_point_serialization(self):
        """DailyCostPoint serializes to JSON-compatible dict."""
        from api.services.admin_analytics_service import DailyCostPoint

        point = DailyCostPoint(
            date="2026-01-31",
            total_cost_usd=50.0,
            total_tokens=5000,
            run_count=10,
        )

        data = point.model_dump()

        assert data["date"] == "2026-01-31"
        assert data["total_cost_usd"] == 50.0

    def test_response_model_serialization(self):
        """Response models serialize correctly."""
        from api.routes.v1.admin import WorkspaceSummariesResponse

        response = WorkspaceSummariesResponse(
            workspaces=[],
            total_cost_usd=250.0,
            total_tokens=25000,
            total_runs=50,
        )

        data = response.model_dump()

        assert data["total_cost_usd"] == 250.0
        assert data["total_tokens"] == 25000
        assert data["total_runs"] == 50
        assert data["workspaces"] == []


class TestEdgeCasesSmoke:
    """Smoke tests for edge cases."""

    def test_zero_values_accepted(self):
        """Models accept zero values."""
        from api.services.admin_analytics_service import (
            WorkspaceCostSummary,
            DailyCostPoint,
            AgentCostBreakdown,
        )

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

        point = DailyCostPoint(
            date="2026-01-01",
            total_cost_usd=0.0,
            total_tokens=0,
            run_count=0,
        )
        assert point.run_count == 0

        breakdown = AgentCostBreakdown(
            agent="test",
            total_cost_usd=0.0,
            total_tokens=0,
            invocation_count=0,
        )
        assert breakdown.invocation_count == 0

    def test_large_values_accepted(self):
        """Models accept large values."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        summary = WorkspaceCostSummary(
            workspace_id=uuid4(),
            workspace_name="Large",
            total_cost_usd=1_000_000.50,
            total_tokens=1_000_000_000,
            run_count=1_000_000,
            successful_runs=999_000,
            failed_runs=1_000,
            last_run_at=None,
        )

        assert summary.total_cost_usd == 1_000_000.50
        assert summary.total_tokens == 1_000_000_000

    def test_null_last_run_accepted(self):
        """WorkspaceCostSummary accepts null last_run_at."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        summary = WorkspaceCostSummary(
            workspace_id=uuid4(),
            workspace_name="New",
            total_cost_usd=0.0,
            total_tokens=0,
            run_count=0,
            successful_runs=0,
            failed_runs=0,
            last_run_at=None,
        )

        assert summary.last_run_at is None

    def test_datetime_last_run_accepted(self):
        """WorkspaceCostSummary accepts datetime for last_run_at."""
        from api.services.admin_analytics_service import WorkspaceCostSummary

        now = datetime.utcnow()
        summary = WorkspaceCostSummary(
            workspace_id=uuid4(),
            workspace_name="Active",
            total_cost_usd=100.0,
            total_tokens=10000,
            run_count=10,
            successful_runs=9,
            failed_runs=1,
            last_run_at=now,
        )

        assert summary.last_run_at == now
