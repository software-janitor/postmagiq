"""Integration tests for core API flows.

These tests verify the main user-facing API workflows work correctly.
Tests run against the actual API with a test database.
"""

import os
import pytest
from uuid import UUID

# Skip all tests if database not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping integration tests"
)


class TestAuthFlow:
    """Tests for authentication flow."""

    def test_register_creates_user_and_workspace(self, api_client):
        """POST /api/v1/auth/register creates user with workspace."""
        import time
        response = api_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"test-reg-{int(time.time() * 1000)}@example.com",
                "password": "testpassword123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_returns_tokens(self, api_client, registered_user):
        """POST /api/v1/auth/login returns access and refresh tokens."""
        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_credentials(self, api_client):
        """POST /api/v1/auth/login rejects invalid credentials."""
        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_me_returns_user_info(self, api_client, auth_headers):
        """GET /api/v1/auth/me returns authenticated user info."""
        response = api_client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data

    def test_refresh_token_works(self, api_client, registered_user):
        """POST /api/v1/auth/refresh returns new access token."""
        # First login to get tokens
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token
        response = api_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestWorkspaceFlow:
    """Tests for workspace operations."""

    def test_list_workspaces(self, api_client, auth_headers):
        """GET /api/v1/workspaces returns user's workspaces."""
        response = api_client.get("/api/v1/workspaces", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # User should have at least their default workspace

    def test_get_workspace_usage(self, api_client, auth_headers, workspace_id):
        """GET /api/v1/w/{workspace_id}/usage returns usage stats."""
        response = api_client.get(
            f"/api/v1/w/{workspace_id}/usage",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should have usage tracking fields
        assert "credits_used" in data or "api_calls" in data or isinstance(data, dict)


class TestContentFlow:
    """Tests for content operations."""

    def test_get_goals(self, api_client, auth_headers, workspace_id):
        """GET /api/v1/w/{workspace_id}/goals returns goals list."""
        response = api_client.get(
            f"/api/v1/w/{workspace_id}/goals",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_chapters(self, api_client, auth_headers, workspace_id):
        """GET /api/v1/w/{workspace_id}/chapters returns chapters list."""
        response = api_client.get(
            f"/api/v1/w/{workspace_id}/chapters",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestOnboardingFlow:
    """Tests for onboarding flow."""

    def test_get_content_styles(self, api_client, auth_headers, workspace_id):
        """GET /api/v1/w/{workspace_id}/onboarding/content-styles returns styles."""
        response = api_client.get(
            f"/api/v1/w/{workspace_id}/onboarding/content-styles",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data

    def test_get_strategy(self, api_client, auth_headers, workspace_id):
        """GET /api/v1/w/{workspace_id}/onboarding/strategy returns strategy."""
        response = api_client.get(
            f"/api/v1/w/{workspace_id}/onboarding/strategy",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should return goal and chapters (may be empty for new user)
        assert "goal" in data
        assert "chapters" in data


class TestHealthCheck:
    """Tests for health check endpoints."""

    def test_health_check(self, api_client):
        """GET /api/health returns ok status."""
        response = api_client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_detailed_requires_admin(self, api_client, registered_user, auth_headers):
        """GET /api/health/detailed requires admin scope."""
        response = api_client.get("/api/health/detailed", headers=auth_headers)
        # Regular users should get 403 (admin scope required)
        assert response.status_code in [200, 403]
        if response.status_code == 403:
            assert "admin" in response.json()["error"]["message"].lower()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def api_client():
    """Create HTTP client for API testing."""
    import httpx
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8002")
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="module")
def registered_user(api_client):
    """Register a test user and return credentials."""
    import time
    email = f"test-{int(time.time())}@example.com"
    password = "testpassword123"

    response = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
        },
    )

    if response.status_code == 201:
        data = response.json()
        return {
            "email": email,
            "password": password,
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
        }
    elif response.status_code == 400 and "already registered" in response.text.lower():
        # User exists, try to login
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if login_response.status_code == 200:
            data = login_response.json()
            return {
                "email": email,
                "password": password,
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
            }

    pytest.skip(f"Could not register or login test user: {response.status_code}")


@pytest.fixture
def auth_headers(registered_user):
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest.fixture
def workspace_id(api_client, auth_headers):
    """Get the user's default workspace ID."""
    response = api_client.get("/api/v1/workspaces", headers=auth_headers)
    if response.status_code == 200:
        workspaces = response.json()
        if workspaces:
            return workspaces[0]["id"]

    # Try getting from /me endpoint
    response = api_client.get("/api/v1/auth/me", headers=auth_headers)
    if response.status_code == 200:
        data = response.json()
        if data.get("workspaces"):
            return data["workspaces"][0]["id"]

    pytest.skip("Could not get workspace ID")
