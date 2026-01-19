"""Integration tests for AI Assistant API.

These tests require CLI tools (gemini, claude) to be authenticated.
Run with: pytest tests/integration/test_ai_assistant.py -v
"""

import pytest
from tests.integration.conftest import SyncClient
from api.main import app


@pytest.fixture
def client():
    """Simple client without database injection - AI assistant doesn't need DB."""
    return SyncClient(app)


class TestAIAssistantChat:
    """Tests for /api/ai-assistant/chat endpoint."""

    @pytest.mark.slow
    def test_gemini_hello_world(self, client):
        """Test Gemini agent responds to a simple hello."""
        response = client.post(
            "/api/ai-assistant/chat",
            json={
                "message": "Say 'Hello World' and nothing else",
                "context": "strategy",
                "agent_type": "gemini",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "hello" in data["response"].lower()

    @pytest.mark.slow
    def test_claude_hello_world(self, client):
        """Test Claude agent responds to a simple hello."""
        response = client.post(
            "/api/ai-assistant/chat",
            json={
                "message": "Say 'Hello World' and nothing else",
                "context": "strategy",
                "agent_type": "claude",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "hello" in data["response"].lower()

    @pytest.mark.slow
    def test_default_agent_is_gemini(self, client):
        """Test that default agent (gemini) works without specifying agent_type."""
        response = client.post(
            "/api/ai-assistant/chat",
            json={
                "message": "Respond with just the word 'yes'",
                "context": "strategy",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["response"]) > 0


class TestAIAssistantContexts:
    """Tests for different context types."""

    @pytest.mark.slow
    def test_strategy_context(self, client):
        """Test strategy context provides relevant assistance."""
        response = client.post(
            "/api/ai-assistant/chat",
            json={
                "message": "What is a signature thesis?",
                "context": "strategy",
                "agent_type": "gemini",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should mention something about thesis or message
        assert len(data["response"]) > 20

    @pytest.mark.slow
    def test_voice_context(self, client):
        """Test voice context provides relevant assistance."""
        response = client.post(
            "/api/ai-assistant/chat",
            json={
                "message": "What is tone in a voice profile?",
                "context": "voice",
                "agent_type": "gemini",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["response"]) > 20

    @pytest.mark.slow
    def test_personas_context(self, client):
        """Test personas context provides relevant assistance."""
        response = client.post(
            "/api/ai-assistant/chat",
            json={
                "message": "What does the Writer persona do?",
                "context": "personas",
                "agent_type": "gemini",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["response"]) > 20

    @pytest.mark.slow
    def test_scenes_context(self, client):
        """Test scenes context provides relevant assistance."""
        response = client.post(
            "/api/ai-assistant/chat",
            json={
                "message": "What is a SUCCESS scene?",
                "context": "scenes",
                "agent_type": "gemini",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["response"]) > 20


class TestAIAssistantAvailableAgents:
    """Tests for /api/ai-assistant/available-agents endpoint."""

    def test_list_available_agents(self, client):
        """Test listing available agents."""
        response = client.get("/api/ai-assistant/available-agents")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) >= 3

        agent_ids = [a["id"] for a in data["agents"]]
        assert "gemini" in agent_ids
        assert "claude" in agent_ids
        assert "ollama" in agent_ids
