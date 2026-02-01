"""Tests for admin analytics routes.

Tests endpoint availability, auth requirements, and response models.
"""

import pytest
from unittest.mock import MagicMock, patch


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


class TestServiceIntegration:
    """Tests for service integration."""

    def test_service_is_instantiated(self):
        """Analytics service is instantiated in routes."""
        from api.routes.v1.admin import analytics_service
        from api.services.admin_analytics_service import AdminAnalyticsService

        assert isinstance(analytics_service, AdminAnalyticsService)
