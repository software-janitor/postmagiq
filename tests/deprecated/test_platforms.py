"""Integration tests for platform API."""

from uuid import UUID, uuid4

import pytest


def _assert_uuid(value: str) -> str:
    UUID(value)
    return value


class TestPlatformCRUD:
    """Tests for platform CRUD operations."""

    def test_create_platform(self, client):
        """Test creating a new platform."""
        # First create a user
        response = client.post("/api/content/users", json={"name": "Test User"})
        assert response.status_code == 200
        user_id = response.json()["id"]

        # Create a platform
        response = client.post(
            "/api/platforms",
            json={
                "user_id": user_id,
                "name": "LinkedIn",
                "description": "52-week thought leadership campaign",
                "post_format": "long-form",
                "default_word_count": 300,
                "uses_enemies": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        _assert_uuid(data["id"])

    def test_get_platforms(self, client):
        """Test getting all platforms for a user."""
        # Create user
        response = client.post("/api/content/users", json={"name": "Test User"})
        user_id = response.json()["id"]

        # Create two platforms
        client.post(
            "/api/platforms",
            json={"user_id": user_id, "name": "LinkedIn", "uses_enemies": True},
        )
        client.post(
            "/api/platforms",
            json={"user_id": user_id, "name": "Threads", "uses_enemies": False},
        )

        # Get platforms
        response = client.get(f"/api/platforms/user/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = [p["name"] for p in data]
        assert "LinkedIn" in names
        assert "Threads" in names

    def test_get_single_platform(self, client):
        """Test getting a single platform."""
        # Create user and platform
        response = client.post("/api/content/users", json={"name": "Test User"})
        user_id = response.json()["id"]

        response = client.post(
            "/api/platforms",
            json={
                "user_id": user_id,
                "name": "LinkedIn",
                "description": "Test desc",
                "default_word_count": 300,
            },
        )
        platform_id = response.json()["id"]

        # Get platform
        response = client.get(f"/api/platforms/{platform_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == platform_id
        assert data["name"] == "LinkedIn"
        assert data["description"] == "Test desc"
        assert data["default_word_count"] == 300

    def test_get_nonexistent_platform(self, client):
        """Test getting a platform that doesn't exist."""
        response = client.get(f"/api/platforms/{uuid4()}")
        assert response.status_code == 404

    def test_update_platform(self, client):
        """Test updating a platform."""
        # Create user and platform
        response = client.post("/api/content/users", json={"name": "Test User"})
        user_id = response.json()["id"]

        response = client.post(
            "/api/platforms",
            json={"user_id": user_id, "name": "LinkedIn", "uses_enemies": True},
        )
        platform_id = response.json()["id"]

        # Update platform
        response = client.put(
            f"/api/platforms/{platform_id}",
            json={"name": "LinkedIn Pro", "uses_enemies": False, "default_word_count": 400},
        )
        assert response.status_code == 200

        # Verify update
        response = client.get(f"/api/platforms/{platform_id}")
        data = response.json()
        assert data["name"] == "LinkedIn Pro"
        assert data["uses_enemies"] is False
        assert data["default_word_count"] == 400

    def test_update_nonexistent_platform(self, client):
        """Test updating a platform that doesn't exist."""
        response = client.put(f"/api/platforms/{uuid4()}", json={"name": "Test"})
        assert response.status_code == 404

    def test_update_no_fields(self, client):
        """Test updating with no fields returns error."""
        # Create user and platform
        response = client.post("/api/content/users", json={"name": "Test User"})
        user_id = response.json()["id"]

        response = client.post(
            "/api/platforms", json={"user_id": user_id, "name": "LinkedIn"}
        )
        platform_id = response.json()["id"]

        # Update with empty body
        response = client.put(f"/api/platforms/{platform_id}", json={})
        assert response.status_code == 400

    def test_delete_platform(self, client):
        """Test deleting a platform."""
        # Create user and platform
        response = client.post("/api/content/users", json={"name": "Test User"})
        user_id = response.json()["id"]

        response = client.post(
            "/api/platforms", json={"user_id": user_id, "name": "LinkedIn"}
        )
        platform_id = response.json()["id"]

        # Delete platform
        response = client.delete(f"/api/platforms/{platform_id}")
        assert response.status_code == 200

        # Verify deleted
        response = client.get(f"/api/platforms/{platform_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_platform(self, client):
        """Test deleting a platform that doesn't exist."""
        response = client.delete(f"/api/platforms/{uuid4()}")
        assert response.status_code == 404


class TestPlatformUsesEnemies:
    """Tests for the uses_enemies field."""

    def test_default_uses_enemies_true(self, client):
        """Test that uses_enemies defaults to True."""
        response = client.post("/api/content/users", json={"name": "Test User"})
        user_id = response.json()["id"]

        response = client.post(
            "/api/platforms", json={"user_id": user_id, "name": "LinkedIn"}
        )
        platform_id = response.json()["id"]

        response = client.get(f"/api/platforms/{platform_id}")
        assert response.json()["uses_enemies"] is True

    def test_can_set_uses_enemies_false(self, client):
        """Test creating a platform without enemies (e.g., for Field Notes only)."""
        response = client.post("/api/content/users", json={"name": "Test User"})
        user_id = response.json()["id"]

        response = client.post(
            "/api/platforms",
            json={
                "user_id": user_id,
                "name": "Threads",
                "uses_enemies": False,
                "post_format": "short-form",
                "default_word_count": 280,
            },
        )
        platform_id = response.json()["id"]

        response = client.get(f"/api/platforms/{platform_id}")
        data = response.json()
        assert data["uses_enemies"] is False
        assert data["post_format"] == "short-form"
        assert data["default_word_count"] == 280
