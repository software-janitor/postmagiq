"""Integration tests for voice API endpoints."""

import pytest


class TestVoiceEndpoints:
    """Tests for /api/voice endpoints."""

    # =========================================================================
    # Prompts Endpoints
    # =========================================================================

    def test_get_prompts(self, client):
        """GET /api/voice/prompts returns all 10 prompts."""
        response = client.get("/api/voice/prompts")
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert len(data["prompts"]) == 10

        # Verify prompt structure
        prompt = data["prompts"][0]
        assert "id" in prompt
        assert "prompt" in prompt
        assert "reveals" in prompt

    def test_get_prompts_ids_unique(self, client):
        """All prompt IDs are unique."""
        response = client.get("/api/voice/prompts")
        prompts = response.json()["prompts"]
        ids = [p["id"] for p in prompts]
        assert len(ids) == len(set(ids))

    def test_get_prompt_by_id(self, client):
        """GET /api/voice/prompts/{id} returns specific prompt."""
        response = client.get("/api/voice/prompts/crisis")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "crisis"
        assert "prompt" in data

    def test_get_prompt_not_found(self, client):
        """GET /api/voice/prompts/{id} returns 404 for invalid ID."""
        response = client.get("/api/voice/prompts/invalid_prompt_id")
        assert response.status_code == 404

    # =========================================================================
    # Samples Endpoints
    # =========================================================================

    def test_save_sample_prompt(self, seeded_client, seeded_user):
        """POST /api/voice/samples saves prompt sample."""
        user_id = str(seeded_user.id)
        response = seeded_client.post(
            "/api/voice/samples",
            json={
                "user_id": user_id,
                "source_type": "prompt",
                "prompt_id": "crisis",
                "content": " ".join(["word"] * 200),  # 200 words
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["word_count"] == 200

    def test_save_sample_upload(self, seeded_client, seeded_user):
        """POST /api/voice/samples saves uploaded content."""
        user_id = str(seeded_user.id)
        response = seeded_client.post(
            "/api/voice/samples",
            json={
                "user_id": user_id,
                "source_type": "upload",
                "title": "My Blog Post",
                "content": "This is my existing blog post content. " * 50,
            },
        )
        assert response.status_code == 200
        assert "id" in response.json()

    def test_save_sample_prompt_exceeds_word_limit(self, seeded_client, seeded_user):
        """POST /api/voice/samples rejects >500 word prompt samples."""
        user_id = str(seeded_user.id)
        response = seeded_client.post(
            "/api/voice/samples",
            json={
                "user_id": user_id,
                "source_type": "prompt",
                "prompt_id": "crisis",
                "content": " ".join(["word"] * 600),  # 600 words
            },
        )
        assert response.status_code == 400
        assert "500 word limit" in response.json()["error"]["message"]

    def test_save_sample_upload_no_word_limit(self, seeded_client, seeded_user):
        """POST /api/voice/samples allows long uploads."""
        user_id = str(seeded_user.id)
        response = seeded_client.post(
            "/api/voice/samples",
            json={
                "user_id": user_id,
                "source_type": "upload",
                "title": "Long Post",
                "content": " ".join(["word"] * 2000),  # 2000 words OK for upload
            },
        )
        assert response.status_code == 200

    def test_get_samples(self, seeded_client, seeded_user):
        """GET /api/voice/users/{id}/samples returns samples with metadata."""
        user_id = str(seeded_user.id)
        # Add samples
        seeded_client.post(
            "/api/voice/samples",
            json={
                "user_id": user_id,
                "source_type": "prompt",
                "prompt_id": "crisis",
                "content": " ".join(["word"] * 300),
            },
        )
        seeded_client.post(
            "/api/voice/samples",
            json={
                "user_id": user_id,
                "source_type": "upload",
                "title": "Blog Post",
                "content": " ".join(["word"] * 200),
            },
        )

        response = seeded_client.get(f"/api/voice/users/{user_id}/samples")
        assert response.status_code == 200
        data = response.json()
        assert "samples" in data
        assert len(data["samples"]) == 2
        assert data["total_word_count"] == 500
        assert data["can_analyze"] is True

    def test_get_samples_empty(self, seeded_client, seeded_user):
        """GET /api/voice/users/{id}/samples returns empty with correct flags."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/voice/users/{user_id}/samples")
        assert response.status_code == 200
        data = response.json()
        assert data["samples"] == []
        assert data["total_word_count"] == 0
        assert data["can_analyze"] is False

    def test_get_sample_status(self, seeded_client, seeded_user):
        """GET /api/voice/users/{id}/samples/status returns analysis readiness."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/voice/users/{user_id}/samples/status")
        assert response.status_code == 200
        data = response.json()
        assert data["sample_count"] == 0
        assert data["total_word_count"] == 0
        assert data["min_words_required"] == 500
        assert data["can_analyze"] is False
        assert data["words_needed"] == 500

    def test_get_sample_status_with_samples(self, seeded_client, seeded_user):
        """GET /api/voice/users/{id}/samples/status updates correctly."""
        user_id = str(seeded_user.id)
        # Add 300 words
        seeded_client.post(
            "/api/voice/samples",
            json={
                "user_id": user_id,
                "source_type": "prompt",
                "prompt_id": "crisis",
                "content": " ".join(["word"] * 300),
            },
        )

        response = seeded_client.get(f"/api/voice/users/{user_id}/samples/status")
        data = response.json()
        assert data["sample_count"] == 1
        assert data["total_word_count"] == 300
        assert data["can_analyze"] is False
        assert data["words_needed"] == 200

    # =========================================================================
    # Profile Endpoints
    # =========================================================================

    def test_get_profile_not_found(self, seeded_client, seeded_user):
        """GET /api/voice/users/{id}/profile returns 404 when no profile."""
        user_id = str(seeded_user.id)
        response = seeded_client.get(f"/api/voice/users/{user_id}/profile")
        assert response.status_code == 404

    def test_get_profile(self, seeded_client, seeded_user):
        """GET /api/voice/users/{id}/profile returns voice profile."""
        user_id = str(seeded_user.id)
        # Create profile via content endpoint
        seeded_client.post(
            "/api/content/voice-profiles",
            json={
                "user_id": user_id,
                "tone": "reflective, warm",
                "vocabulary_level": "technical",
                "storytelling_style": "in-media-res",
                "emotional_register": "vulnerable",
                "sentence_patterns": '{"avg_length": 15}',
                "signature_phrases": '["I learned", "What I realized"]',
            },
        )

        response = seeded_client.get(f"/api/voice/users/{user_id}/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["tone"] == "reflective, warm"
        assert data["vocabulary_level"] == "technical"

    # =========================================================================
    # Analysis Endpoint
    # =========================================================================

    def test_analyze_insufficient_words(self, seeded_client, seeded_user):
        """POST /api/voice/analyze rejects when not enough samples."""
        user_id = str(seeded_user.id)
        response = seeded_client.post(
            "/api/voice/analyze",
            json={"user_id": user_id},
        )
        assert response.status_code == 400
        assert "500 words" in response.json()["error"]["message"]

    # Note: Full analysis test requires LLM integration or mocking
    # The analyze endpoint calls an LLM which we don't want in unit tests


class TestVoicePromptContent:
    """Tests for voice prompt content quality."""

    def test_prompts_cover_different_aspects(self, client):
        """Voice prompts cover diverse writing aspects."""
        response = client.get("/api/voice/prompts")
        prompts = response.json()["prompts"]

        # Check that reveals describe different aspects
        reveals = [p["reveals"] for p in prompts]
        assert len(set(reveals)) >= 8  # At least 8 unique aspects

    def test_prompts_are_open_ended(self, client):
        """Voice prompts encourage narrative responses."""
        response = client.get("/api/voice/prompts")
        prompts = response.json()["prompts"]

        # Check that prompts don't end with yes/no questions
        for prompt in prompts:
            text = prompt["prompt"].lower()
            assert not text.endswith("?") or "why" in text or "how" in text
