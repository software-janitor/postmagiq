"""Integration tests for content API endpoints."""

from uuid import UUID, uuid4

import pytest


def _assert_uuid(value: str) -> str:
    UUID(value)
    return value


class TestContentEndpoints:
    """Tests for /api/content endpoints."""

    # =========================================================================
    # User Endpoints
    # =========================================================================

    def test_create_user(self, client):
        """POST /api/content/users creates a new user."""
        response = client.post(
            "/api/content/users",
            json={"name": "John Doe", "email": "john@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        _assert_uuid(data["id"])

    def test_create_user_without_email(self, client):
        """POST /api/content/users works without email."""
        response = client.post(
            "/api/content/users",
            json={"name": "Jane Doe"},
        )
        assert response.status_code == 200
        _assert_uuid(response.json()["id"])

    def test_get_user(self, seeded_client, seeded_user):
        """GET /api/content/users/{id} returns user with summary."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/content/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["has_goal"] is True
        assert data["has_voice_profile"] is False
        assert data["post_count"] == 6

    def test_get_user_not_found(self, client):
        """GET /api/content/users/{id} returns 404 for missing user."""
        response = client.get(f"/api/content/users/{uuid4()}")
        assert response.status_code == 404
        assert response.json()["error"]["message"] == "User not found"

    def test_get_user_by_email(self, seeded_client):
        """GET /api/content/users/email/{email} finds user."""
        response = seeded_client.get("/api/content/users/email/test@example.com")
        assert response.status_code == 200
        assert response.json()["name"] == "Test User"

    def test_get_user_by_email_not_found(self, client):
        """GET /api/content/users/email/{email} returns 404."""
        response = client.get("/api/content/users/email/missing@example.com")
        assert response.status_code == 404

    # =========================================================================
    # Goal Endpoints
    # =========================================================================

    def test_save_goal(self, client):
        """POST /api/content/goals creates a goal."""
        create = client.post("/api/content/users", json={"name": "Test User"})
        user_id = create.json()["id"]

        response = client.post(
            "/api/content/goals",
            json={
                "user_id": user_id,
                "positioning": "Tech Lead",
                "signature_thesis": "AI needs systems",
                "target_audience": "Engineers",
                "content_style": "teaching",
            },
        )
        assert response.status_code == 200
        _assert_uuid(response.json()["id"])

    def test_get_goal(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/goal returns goal."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/content/users/{user_id}/goal")
        assert response.status_code == 200
        data = response.json()
        assert data["positioning"] == "Senior Engineer"
        assert data["signature_thesis"] == "Test thesis"
        assert data["content_style"] == "teaching"

    def test_get_goal_not_found(self, client):
        """GET /api/content/users/{id}/goal returns 404."""
        create = client.post("/api/content/users", json={"name": "No Goal User"})
        user_id = create.json()["id"]
        response = client.get(f"/api/content/users/{user_id}/goal")
        assert response.status_code == 404

    def test_update_goal(self, seeded_client, seeded_user):
        """PUT /api/content/goals/{id} updates goal."""
        user_id = str(seeded_user.id)
        goal = seeded_client.get(f"/api/content/users/{user_id}/goal").json()
        goal_id = goal["id"]

        response = seeded_client.put(
            f"/api/content/goals/{goal_id}",
            json={"positioning": "Staff Engineer"},
        )
        assert response.status_code == 200

        # Verify update
        response = seeded_client.get(f"/api/content/users/{user_id}/goal")
        assert response.json()["positioning"] == "Staff Engineer"

    def test_update_goal_empty_request(self, seeded_client, seeded_user):
        """PUT /api/content/goals/{id} with no fields returns 400."""
        user_id = str(seeded_user.id)
        goal = seeded_client.get(f"/api/content/users/{user_id}/goal").json()
        response = seeded_client.put(f"/api/content/goals/{goal['id']}", json={})
        assert response.status_code == 400

    # =========================================================================
    # Chapter Endpoints
    # =========================================================================

    def test_save_chapter(self, client):
        """POST /api/content/chapters creates a chapter."""
        create = client.post("/api/content/users", json={"name": "Test User"})
        user_id = create.json()["id"]

        response = client.post(
            "/api/content/chapters",
            json={
                "user_id": user_id,
                "chapter_number": 1,
                "title": "Getting Started",
                "theme": "Introduction",
                "weeks_start": 1,
                "weeks_end": 4,
            },
        )
        assert response.status_code == 200
        _assert_uuid(response.json()["id"])

    def test_get_chapters(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/chapters returns all chapters."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/content/users/{user_id}/chapters")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["chapter_number"] == 1
        assert data[0]["title"] == "Chapter 1"
        assert "post_count" in data[0]
        assert "completed_count" in data[0]

    def test_get_chapter(self, seeded_client, seeded_user):
        """GET /api/content/chapters/{id} returns single chapter."""
        user_id = str(seeded_user.id)
        chapters = seeded_client.get(f"/api/content/users/{user_id}/chapters").json()
        chapter_id = chapters[0]["id"]

        response = seeded_client.get(f"/api/content/chapters/{chapter_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Chapter 1"
        assert data["post_count"] == 3  # 3 posts in chapter 1

    def test_get_chapter_not_found(self, client):
        """GET /api/content/chapters/{id} returns 404."""
        response = client.get(f"/api/content/chapters/{uuid4()}")
        assert response.status_code == 404

    # =========================================================================
    # Post Endpoints
    # =========================================================================

    def test_save_post(self, client):
        """POST /api/content/posts creates a post."""
        create = client.post("/api/content/users", json={"name": "Test User"})
        user_id = create.json()["id"]
        chapter = client.post(
            "/api/content/chapters",
            json={"user_id": user_id, "chapter_number": 1, "title": "Ch1"},
        )
        chapter_id = chapter.json()["id"]

        response = client.post(
            "/api/content/posts",
            json={
                "user_id": user_id,
                "chapter_id": chapter_id,
                "post_number": 1,
                "topic": "First post",
                "shape": "FULL",
                "status": "not_started",
            },
        )
        assert response.status_code == 200
        _assert_uuid(response.json()["id"])

    def test_get_posts(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/posts returns all posts."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/content/users/{user_id}/posts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6

    def test_get_posts_filtered_by_chapter(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/posts?chapter_id=X filters."""
        user_id = str(seeded_user.id)
        chapters = seeded_client.get(f"/api/content/users/{user_id}/chapters").json()
        chapter_id = chapters[0]["id"]
        response = seeded_client.get(
            f"/api/content/users/{user_id}/posts?chapter_id={chapter_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(p["chapter_id"] == chapter_id for p in data)

    def test_get_posts_filtered_by_status(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/posts?status=X filters."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/content/users/{user_id}/posts?status=not_started")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(p["status"] == "not_started" for p in data)

    def test_get_available_posts(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/posts/available returns work items."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/content/users/{user_id}/posts/available")
        assert response.status_code == 200
        data = response.json()
        # Should return not_started, needs_story, draft (not ready/published)
        assert len(data) == 4
        statuses = {p["status"] for p in data}
        assert "published" not in statuses
        assert "ready" not in statuses

    def test_get_next_post(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/posts/next returns first available."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/content/users/{user_id}/posts/next")
        assert response.status_code == 200
        data = response.json()
        # Should be the lowest post_number that's not ready/published
        assert data["status"] in ["not_started", "needs_story", "draft"]

    def test_get_next_post_none_available(self, client):
        """GET /api/content/users/{id}/posts/next returns 404 when done."""
        create = client.post("/api/content/users", json={"name": "Test User"})
        user_id = create.json()["id"]
        response = client.get(f"/api/content/users/{user_id}/posts/next")
        assert response.status_code == 404

    def test_get_post(self, seeded_client, seeded_user):
        """GET /api/content/posts/{id} returns single post."""
        user_id = str(seeded_user.id)
        posts = seeded_client.get(f"/api/content/users/{user_id}/posts").json()
        post_id = posts[0]["id"]
        response = seeded_client.get(f"/api/content/posts/{post_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == post_id
        assert "topic" in data
        assert "chapter_title" in data

    def test_update_post(self, seeded_client, seeded_user):
        """PUT /api/content/posts/{id} updates post."""
        user_id = str(seeded_user.id)
        posts = seeded_client.get(f"/api/content/users/{user_id}/posts").json()
        post_id = posts[0]["id"]
        response = seeded_client.put(
            f"/api/content/posts/{post_id}",
            json={"status": "published", "published_url": "https://linkedin.com/1"},
        )
        assert response.status_code == 200

        # Verify update
        response = seeded_client.get(f"/api/content/posts/{post_id}")
        assert response.json()["status"] == "published"
        assert response.json()["published_url"] == "https://linkedin.com/1"

    # =========================================================================
    # Writing Sample Endpoints
    # =========================================================================

    def test_save_writing_sample(self, seeded_client, seeded_user):
        """POST /api/content/samples saves a sample."""
        user_id = str(seeded_user.id)
        response = seeded_client.post(
            "/api/content/samples",
            json={
                "user_id": user_id,
                "source_type": "prompt",
                "content": "This is a test writing sample with enough words.",
                "prompt_id": "story_crisis",
            },
        )
        assert response.status_code == 200
        _assert_uuid(response.json()["id"])

    def test_get_writing_samples(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/samples returns samples."""
        user_id = str(seeded_user.id)
        # Add a sample first
        seeded_client.post(
            "/api/content/samples",
            json={
                "user_id": user_id,
                "source_type": "upload",
                "content": "Sample content here",
                "title": "My Blog Post",
            },
        )

        response = seeded_client.get(f"/api/content/users/{user_id}/samples")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "My Blog Post"

    # =========================================================================
    # Voice Profile Endpoints
    # =========================================================================

    def test_save_voice_profile(self, seeded_client, seeded_user):
        """POST /api/content/voice-profiles saves a profile."""
        user_id = str(seeded_user.id)
        response = seeded_client.post(
            "/api/content/voice-profiles",
            json={
                "user_id": user_id,
                "tone": "reflective, warm",
                "vocabulary_level": "technical",
                "storytelling_style": "in-media-res",
            },
        )
        assert response.status_code == 200
        _assert_uuid(response.json()["id"])

    def test_get_voice_profile(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/voice-profile returns profile."""
        user_id = str(seeded_user.id)
        # Add a profile first
        seeded_client.post(
            "/api/content/voice-profiles",
            json={
                "user_id": user_id,
                "tone": "direct",
                "vocabulary_level": "accessible",
            },
        )

        response = seeded_client.get(f"/api/content/users/{user_id}/voice-profile")
        assert response.status_code == 200
        data = response.json()
        assert data["tone"] == "direct"
        assert data["vocabulary_level"] == "accessible"

    def test_get_voice_profile_not_found(self, seeded_client, seeded_user):
        """GET /api/content/users/{id}/voice-profile returns 404."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/content/users/{user_id}/voice-profile")
        assert response.status_code == 404

    def test_update_voice_profile(self, seeded_client, seeded_user):
        """PUT /api/content/voice-profiles/{id} updates profile."""
        user_id = str(seeded_user.id)
        # Create profile first
        create = seeded_client.post(
            "/api/content/voice-profiles",
            json={"user_id": user_id, "tone": "warm"},
        )
        profile_id = create.json()["id"]

        response = seeded_client.put(
            f"/api/content/voice-profiles/{profile_id}",
            json={"tone": "direct and confident"},
        )
        assert response.status_code == 200

        # Verify
        response = seeded_client.get(f"/api/content/users/{user_id}/voice-profile")
        assert response.json()["tone"] == "direct and confident"

    # =========================================================================
    # Constants Endpoints
    # =========================================================================

    def test_get_voice_prompts(self, client):
        """GET /api/content/prompts returns voice prompts."""
        response = client.get("/api/content/prompts")
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert len(data["prompts"]) == 10

    def test_get_content_styles(self, client):
        """GET /api/content/styles returns content styles."""
        response = client.get("/api/content/styles")
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        assert len(data["styles"]) > 0
        # Check structure
        assert "id" in data["styles"][0]
        assert "name" in data["styles"][0]

    def test_get_post_shapes(self, client):
        """GET /api/content/shapes returns post shapes."""
        response = client.get("/api/content/shapes")
        assert response.status_code == 200
        data = response.json()
        assert "shapes" in data
        # Should have FULL, PARTIAL, OBSERVATION, SHORT, REVERSAL
        shape_ids = [s["id"] for s in data["shapes"]]
        assert "FULL" in shape_ids
        assert "PARTIAL" in shape_ids
