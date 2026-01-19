"""Integration tests for onboarding API endpoints."""

from uuid import UUID, uuid4

import pytest


def _assert_uuid(value: str) -> str:
    UUID(value)
    return value


class TestOnboardingEndpoints:
    """Tests for /api/onboarding endpoints."""

    # =========================================================================
    # Start Onboarding
    # =========================================================================

    def test_start_onboarding_creates_user(self, client):
        """POST /api/onboarding/start creates user and returns questions."""
        response = client.post(
            "/api/onboarding/start",
            json={"name": "New User", "email": "new@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        _assert_uuid(data["user_id"])
        assert "questions" in data
        assert len(data["questions"]) > 0

    def test_start_onboarding_returns_existing_user(self, seeded_client, seeded_user):
        """POST /api/onboarding/start finds existing user by email."""
        response = seeded_client.post(
            "/api/onboarding/start",
            json={"name": "Ignored Name", "email": "test@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(seeded_user.id)

    def test_start_onboarding_without_email(self, client):
        """POST /api/onboarding/start works without email."""
        response = client.post(
            "/api/onboarding/start",
            json={"name": "Anonymous User"},
        )
        assert response.status_code == 200
        _assert_uuid(response.json()["user_id"])

    # =========================================================================
    # Quick Mode Questions
    # =========================================================================

    def test_get_quick_questions(self, client):
        """GET /api/onboarding/questions returns quick mode questions."""
        response = client.get("/api/onboarding/questions")
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        questions = data["questions"]
        assert len(questions) >= 5

        # Verify question structure
        q = questions[0]
        assert "id" in q
        assert "question" in q
        # Questions should have either options or be freeform
        assert "options" in q or "type" in q

    def test_quick_questions_cover_essentials(self, client):
        """Quick mode questions ask about role, goals, audience, style."""
        response = client.get("/api/onboarding/questions")
        questions = response.json()["questions"]
        question_ids = [q["id"] for q in questions]

        # Should have these essential questions
        assert "professional_role" in question_ids
        assert "known_for" in question_ids
        assert "target_audience" in question_ids
        assert "content_style" in question_ids

    # =========================================================================
    # Quick Mode Processing
    # =========================================================================

    def test_quick_mode_validates_required_fields(self, client):
        """POST /api/onboarding/quick validates required fields."""
        start = client.post("/api/onboarding/start", json={"name": "Test"})
        user_id = start.json()["user_id"]
        response = client.post(
            "/api/onboarding/quick",
            json={
                "user_id": user_id,
                # Missing required fields
            },
        )
        assert response.status_code == 400  # Validation error (standardized)

    def test_quick_mode_request_structure(self, client):
        """POST /api/onboarding/quick accepts correct structure."""
        start = client.post("/api/onboarding/start", json={"name": "Test"})
        user_id = start.json()["user_id"]

        response = client.post(
            "/api/onboarding/quick",
            json={
                "user_id": user_id,
                "professional_role": "Senior Engineer",
                "known_for": "AI systems",
                "target_audience": "Tech leaders",
                "content_style": "teaching",
                "posts_per_week": 2,
            },
        )
        # Should not fail with validation error
        # Will fail with 500 if no LLM configured, which is expected
        assert response.status_code in [200, 500]

    # =========================================================================
    # Deep Mode
    # =========================================================================

    def test_deep_start_response_structure(self, client):
        """POST /api/onboarding/deep/start returns correct structure."""
        response = client.post("/api/onboarding/deep/start")
        # Will fail with 500 if no LLM, but should not be 422
        assert response.status_code in [200, 500]

    def test_deep_message_requires_state(self, client):
        """POST /api/onboarding/deep/message requires state."""
        response = client.post(
            "/api/onboarding/deep/message",
            json={"user_id": str(uuid4()), "message": "Test message"},
        )
        assert response.status_code == 400
        assert "State required" in response.json()["error"]["message"]

    # =========================================================================
    # Plan Approval
    # =========================================================================

    def test_approve_plan(self, client):
        """POST /api/onboarding/approve saves plan to database."""
        # Create user first
        start = client.post("/api/onboarding/start", json={"name": "Test User"})
        user_id = start.json()["user_id"]

        response = client.post(
            "/api/onboarding/approve",
            json={
                "user_id": user_id,
                "plan": {
                    "signature_thesis": "AI needs systems to work",
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "title": "Chapter 1",
                            "theme": "Introduction",
                            "theme_description": "Getting started",
                            "posts": [
                                {"topic": "Post 1", "shape": "FULL"},
                                {"topic": "Post 2", "shape": "PARTIAL"},
                            ],
                        },
                        {
                            "chapter_number": 2,
                            "title": "Chapter 2",
                            "theme": "Advanced",
                            "theme_description": "Going deeper",
                            "posts": [
                                {"topic": "Post 3", "shape": "OBSERVATION"},
                            ],
                        },
                    ],
                },
                "positioning": "AI Systems Expert",
                "target_audience": "Engineering Leaders",
                "content_style": "teaching",
                "onboarding_mode": "quick",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "goal_id" in data
        assert data["chapter_count"] == 2
        assert data["post_count"] == 3

    def test_approve_plan_validates_structure(self, seeded_client, seeded_user):
        """POST /api/onboarding/approve validates plan structure."""
        response = seeded_client.post(
            "/api/onboarding/approve",
            json={
                "user_id": str(seeded_user.id),
                "plan": {
                    # Missing required fields
                },
                "positioning": "Test",
                "target_audience": "Test",
                "content_style": "teaching",
                "onboarding_mode": "quick",
            },
        )
        # Should fail validation
        assert response.status_code in [422, 500]


class TestOnboardingWorkflow:
    """Tests for complete onboarding workflows."""

    def test_start_then_approve_creates_complete_setup(self, client):
        """Full onboarding flow creates user, goal, chapters, posts."""
        # Start onboarding
        start_response = client.post(
            "/api/onboarding/start",
            json={"name": "Flow Test User", "email": "flow@test.com"},
        )
        user_id = start_response.json()["user_id"]

        # Approve a plan
        approve_response = client.post(
            "/api/onboarding/approve",
            json={
                "user_id": user_id,
                "plan": {
                    "signature_thesis": "Test thesis",
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "title": "Getting Started",
                            "theme": "Basics",
                            "theme_description": "Introduction",
                            "posts": [
                                {"topic": "First Post", "shape": "FULL"},
                                {"topic": "Second Post", "shape": "SHORT"},
                            ],
                        },
                    ],
                },
                "positioning": "Test Position",
                "target_audience": "Testers",
                "content_style": "narrative",
                "onboarding_mode": "quick",
            },
        )
        assert approve_response.status_code == 200

        # Verify everything was created
        user_response = client.get(f"/api/content/users/{user_id}")
        assert user_response.status_code == 200
        user = user_response.json()
        assert user["has_goal"] is True
        assert user["post_count"] == 2

        # Verify goal
        goal_response = client.get(f"/api/content/users/{user_id}/goal")
        assert goal_response.status_code == 200
        goal = goal_response.json()
        assert goal["positioning"] == "Test Position"
        assert goal["signature_thesis"] == "Test thesis"

        # Verify chapters
        chapters_response = client.get(f"/api/content/users/{user_id}/chapters")
        assert chapters_response.status_code == 200
        chapters = chapters_response.json()
        assert len(chapters) == 1
        assert chapters[0]["title"] == "Getting Started"

        # Verify posts
        posts_response = client.get(f"/api/content/users/{user_id}/posts")
        assert posts_response.status_code == 200
        posts = posts_response.json()
        assert len(posts) == 2
        assert posts[0]["topic"] == "First Post"

    def test_returning_user_can_add_goal(self, client):
        """User can add multiple goals over time."""
        start = client.post("/api/onboarding/start", json={"name": "Test User"})
        user_id = start.json()["user_id"]

        client.post(
            "/api/onboarding/approve",
            json={
                "user_id": user_id,
                "plan": {
                    "signature_thesis": "First thesis",
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "title": "First Chapter",
                            "theme": "Beginning",
                            "theme_description": "Starting out",
                            "posts": [{"topic": "First Post", "shape": "FULL"}],
                        },
                    ],
                },
                "positioning": "First Position",
                "target_audience": "First Audience",
                "content_style": "teaching",
                "onboarding_mode": "quick",
            },
        )

        # Verify first goal
        goal_response = client.get(f"/api/content/users/{user_id}/goal")
        assert goal_response.status_code == 200
        assert goal_response.json()["positioning"] == "First Position"

        response = client.post(
            "/api/onboarding/approve",
            json={
                "user_id": user_id,
                "plan": {
                    "signature_thesis": "Updated thesis",
                    "chapters": [],  # No new chapters to avoid conflicts
                },
                "positioning": "Updated Position",
                "target_audience": "New Audience",
                "content_style": "informational",
                "onboarding_mode": "deep",
            },
        )
        assert response.status_code == 200

        # Most recent goal should be returned
        goal_response = client.get(f"/api/content/users/{user_id}/goal")
        goal = goal_response.json()
        assert goal["positioning"] == "Updated Position"
        assert goal["signature_thesis"] == "Updated thesis"
