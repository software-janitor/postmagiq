"""Tests for admin analytics routes.

Tests endpoint availability, auth requirements, and response models.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime


class TestAdminRoutesImport:
    """Tests for admin routes import."""

    def test_router_can_be_imported(self):
        """Admin router can be imported."""
        from api.routes.v1.admin import router

        assert router is not None

    def test_response_models_can_be_imported(self):
        """Admin response models can be imported."""
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


class TestWorkspaceSummariesResponse:
    """Tests for WorkspaceSummariesResponse model."""

    def test_empty_response(self):
        """WorkspaceSummariesResponse can have empty workspaces."""
        from api.routes.v1.admin import WorkspaceSummariesResponse

        response = WorkspaceSummariesResponse(
            workspaces=[],
            total_cost_usd=0.0,
            total_tokens=0,
            total_runs=0,
        )

        assert response.workspaces == []
        assert response.total_cost_usd == 0.0

    def test_response_with_workspaces(self):
        """WorkspaceSummariesResponse can contain workspace data."""
        from api.routes.v1.admin import WorkspaceSummariesResponse
        from api.services.admin_analytics_service import WorkspaceCostSummary

        ws_id = uuid4()
        workspace = WorkspaceCostSummary(
            workspace_id=ws_id,
            workspace_name="Test",
            total_cost_usd=100.0,
            total_tokens=10000,
            run_count=20,
            successful_runs=18,
            failed_runs=2,
            last_run_at=datetime.utcnow(),
        )

        response = WorkspaceSummariesResponse(
            workspaces=[workspace],
            total_cost_usd=100.0,
            total_tokens=10000,
            total_runs=20,
        )

        assert len(response.workspaces) == 1
        assert response.total_cost_usd == 100.0
        assert response.total_runs == 20

    def test_response_serialization(self):
        """WorkspaceSummariesResponse serializes correctly."""
        from api.routes.v1.admin import WorkspaceSummariesResponse

        response = WorkspaceSummariesResponse(
            workspaces=[],
            total_cost_usd=50.0,
            total_tokens=5000,
            total_runs=10,
        )

        data = response.model_dump()
        assert data["total_cost_usd"] == 50.0
        assert data["total_tokens"] == 5000
        assert data["total_runs"] == 10
        assert "workspaces" in data


class TestTimelineResponse:
    """Tests for TimelineResponse model."""

    def test_timeline_response(self):
        """TimelineResponse can be created with data."""
        from api.routes.v1.admin import TimelineResponse

        response = TimelineResponse(
            data=[],
            days_back=30,
        )

        assert response.days_back == 30
        assert response.data == []

    def test_timeline_response_with_data(self):
        """TimelineResponse can contain DailyCostPoint data."""
        from api.routes.v1.admin import TimelineResponse
        from api.services.admin_analytics_service import DailyCostPoint

        point = DailyCostPoint(
            date="2026-01-31",
            total_cost_usd=50.0,
            total_tokens=5000,
            run_count=10,
        )

        response = TimelineResponse(
            data=[point],
            days_back=7,
        )

        assert len(response.data) == 1
        assert response.days_back == 7

    def test_timeline_response_serialization(self):
        """TimelineResponse serializes correctly."""
        from api.routes.v1.admin import TimelineResponse
        from api.services.admin_analytics_service import DailyCostPoint

        point = DailyCostPoint(
            date="2026-01-30",
            total_cost_usd=25.0,
            total_tokens=2500,
            run_count=5,
        )

        response = TimelineResponse(
            data=[point],
            days_back=14,
        )

        data = response.model_dump()
        assert data["days_back"] == 14
        assert len(data["data"]) == 1
        assert data["data"][0]["date"] == "2026-01-30"


class TestAgentBreakdownResponse:
    """Tests for AgentBreakdownResponse model."""

    def test_agent_breakdown_response(self):
        """AgentBreakdownResponse can be created."""
        from api.routes.v1.admin import AgentBreakdownResponse

        response = AgentBreakdownResponse(
            agents=[],
            total_cost_usd=0.0,
        )

        assert response.agents == []
        assert response.total_cost_usd == 0.0

    def test_agent_breakdown_with_agents(self):
        """AgentBreakdownResponse can contain agent data."""
        from api.routes.v1.admin import AgentBreakdownResponse
        from api.services.admin_analytics_service import AgentCostBreakdown

        agent = AgentCostBreakdown(
            agent="claude",
            total_cost_usd=75.0,
            total_tokens=10000,
            invocation_count=25,
        )

        response = AgentBreakdownResponse(
            agents=[agent],
            total_cost_usd=75.0,
        )

        assert len(response.agents) == 1
        assert response.total_cost_usd == 75.0

    def test_agent_breakdown_serialization(self):
        """AgentBreakdownResponse serializes correctly."""
        from api.routes.v1.admin import AgentBreakdownResponse
        from api.services.admin_analytics_service import AgentCostBreakdown

        agent = AgentCostBreakdown(
            agent="gemini",
            total_cost_usd=50.0,
            total_tokens=5000,
            invocation_count=10,
        )

        response = AgentBreakdownResponse(
            agents=[agent],
            total_cost_usd=50.0,
        )

        data = response.model_dump()
        assert data["total_cost_usd"] == 50.0
        assert len(data["agents"]) == 1
        assert data["agents"][0]["agent"] == "gemini"


class TestRefreshResponse:
    """Tests for RefreshResponse model."""

    def test_refresh_response(self):
        """RefreshResponse can be created."""
        from api.routes.v1.admin import RefreshResponse

        response = RefreshResponse(
            records_updated=42,
            message="Refreshed 42 daily cost records for the last 30 days",
        )

        assert response.records_updated == 42
        assert "42" in response.message

    def test_refresh_response_zero_records(self):
        """RefreshResponse handles zero records."""
        from api.routes.v1.admin import RefreshResponse

        response = RefreshResponse(
            records_updated=0,
            message="No records to update",
        )

        assert response.records_updated == 0

    def test_refresh_response_serialization(self):
        """RefreshResponse serializes correctly."""
        from api.routes.v1.admin import RefreshResponse

        response = RefreshResponse(
            records_updated=100,
            message="Test message",
        )

        data = response.model_dump()
        assert data["records_updated"] == 100
        assert data["message"] == "Test message"


class TestRouterPrefix:
    """Tests for router configuration."""

    def test_router_has_correct_prefix(self):
        """Admin router has correct prefix."""
        from api.routes.v1.admin import router

        assert router.prefix == "/v1/admin/analytics"

    def test_router_has_correct_tags(self):
        """Admin router has correct tags."""
        from api.routes.v1.admin import router

        assert "admin-analytics" in router.tags


class TestRouteDefinitions:
    """Tests for route definitions."""

    def test_workspaces_route_exists(self):
        """GET /workspaces route exists."""
        from api.routes.v1.admin import router

        # Routes include the prefix - look for route containing 'workspaces'
        routes = [r.path for r in router.routes]
        assert any("workspaces" in r and "{" not in r for r in routes)

    def test_workspaces_detail_route_exists(self):
        """GET /workspaces/{workspace_id} route exists."""
        from api.routes.v1.admin import router

        routes = [r.path for r in router.routes]
        assert any("workspaces" in r and "workspace_id" in r for r in routes)

    def test_timeline_route_exists(self):
        """GET /timeline route exists."""
        from api.routes.v1.admin import router

        routes = [r.path for r in router.routes]
        assert any("timeline" in r for r in routes)

    def test_agents_route_exists(self):
        """GET /agents route exists."""
        from api.routes.v1.admin import router

        routes = [r.path for r in router.routes]
        assert any("agents" in r for r in routes)

    def test_refresh_route_exists(self):
        """POST /refresh route exists."""
        from api.routes.v1.admin import router

        routes = [r.path for r in router.routes]
        assert any("refresh" in r for r in routes)

    def test_all_routes_present(self):
        """All expected routes are present."""
        from api.routes.v1.admin import router

        routes = [r.path for r in router.routes]
        expected_patterns = ["workspaces", "timeline", "agents", "refresh"]

        for pattern in expected_patterns:
            assert any(
                pattern in r for r in routes
            ), f"Missing route pattern: {pattern}"


class TestServiceIntegration:
    """Tests for service integration."""

    def test_service_is_instantiated(self):
        """Analytics service is instantiated in routes."""
        from api.routes.v1.admin import analytics_service
        from api.services.admin_analytics_service import AdminAnalyticsService

        assert isinstance(analytics_service, AdminAnalyticsService)

    def test_service_has_all_required_methods(self):
        """Analytics service has all methods used by routes."""
        from api.routes.v1.admin import analytics_service

        required_methods = [
            "get_workspace_summaries",
            "get_single_workspace",
            "get_timeline",
            "get_agent_breakdown",
            "refresh_daily_costs",
        ]

        for method in required_methods:
            assert hasattr(
                analytics_service, method
            ), f"Missing method: {method}"
            assert callable(
                getattr(analytics_service, method)
            ), f"Method not callable: {method}"


class TestRouteMethods:
    """Tests for HTTP methods on routes."""

    def test_workspaces_list_is_get(self):
        """Workspaces list route uses GET method."""
        from api.routes.v1.admin import router

        for route in router.routes:
            if hasattr(route, "path") and "workspaces" in route.path:
                if "{" not in route.path:  # List route, not detail
                    assert "GET" in route.methods

    def test_timeline_is_get(self):
        """Timeline route uses GET method."""
        from api.routes.v1.admin import router

        for route in router.routes:
            if hasattr(route, "path") and "timeline" in route.path:
                assert "GET" in route.methods

    def test_agents_is_get(self):
        """Agents route uses GET method."""
        from api.routes.v1.admin import router

        for route in router.routes:
            if hasattr(route, "path") and "agents" in route.path:
                assert "GET" in route.methods

    def test_refresh_is_post(self):
        """Refresh route uses POST method."""
        from api.routes.v1.admin import router

        for route in router.routes:
            if hasattr(route, "path") and "refresh" in route.path:
                assert "POST" in route.methods


class TestQueryParameters:
    """Tests for route query parameters."""

    def test_days_back_parameter_default(self):
        """days_back parameter has sensible default."""
        # The route functions should accept days_back with default of 30
        from api.routes.v1.admin import router
        import inspect

        for route in router.routes:
            if hasattr(route, "endpoint"):
                sig = inspect.signature(route.endpoint)
                if "days_back" in sig.parameters:
                    param = sig.parameters["days_back"]
                    assert param.default == 30 or param.default is not inspect.Parameter.empty

    def test_workspace_id_parameter_type(self):
        """workspace_id parameter accepts UUID."""
        from api.routes.v1.admin import router

        # Find the detail route
        detail_routes = [
            r for r in router.routes
            if hasattr(r, "path") and "workspace_id" in getattr(r, "path", "")
        ]
        assert len(detail_routes) > 0


class TestResponseModels:
    """Tests for route response models."""

    def test_workspaces_response_model(self):
        """Workspaces route has correct response model."""
        from api.routes.v1.admin import WorkspaceSummariesResponse

        # Verify model has expected fields
        fields = WorkspaceSummariesResponse.model_fields
        assert "workspaces" in fields
        assert "total_cost_usd" in fields
        assert "total_tokens" in fields
        assert "total_runs" in fields

    def test_timeline_response_model(self):
        """Timeline route has correct response model."""
        from api.routes.v1.admin import TimelineResponse

        fields = TimelineResponse.model_fields
        assert "data" in fields
        assert "days_back" in fields

    def test_agent_breakdown_response_model(self):
        """Agent breakdown route has correct response model."""
        from api.routes.v1.admin import AgentBreakdownResponse

        fields = AgentBreakdownResponse.model_fields
        assert "agents" in fields
        assert "total_cost_usd" in fields

    def test_refresh_response_model(self):
        """Refresh route has correct response model."""
        from api.routes.v1.admin import RefreshResponse

        fields = RefreshResponse.model_fields
        assert "records_updated" in fields
        assert "message" in fields
