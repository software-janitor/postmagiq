"""Integration tests for model selection in CLI agents.

These tests make real API calls and cost money.
Run with: pytest tests/integration/test_model_selection.py -v

Skip with: pytest -m "not live"
"""

import os
import pytest

from runner.agents import ClaudeAgent, GeminiAgent, CodexAgent


# Mark all tests in this module as live (require real API access)
pytestmark = pytest.mark.live


@pytest.fixture
def session_dir(tmp_path):
    """Provide a temporary session directory."""
    return str(tmp_path / "sessions")


class TestClaudeModelSelection:
    """Test Claude CLI with different model selections."""

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_claude_sonnet_hello_world(self, session_dir):
        """Test Claude with sonnet model."""
        agent = ClaudeAgent({"model": "sonnet"}, session_dir)
        result = agent.invoke("Respond with exactly: Hello World")

        assert result.success, f"Failed: {result.error}"
        assert "Hello" in result.content or "hello" in result.content.lower()

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_claude_haiku_hello_world(self, session_dir):
        """Test Claude with haiku model (fastest/cheapest)."""
        agent = ClaudeAgent({"model": "haiku"}, session_dir)
        result = agent.invoke("Respond with exactly: Hello World")

        assert result.success, f"Failed: {result.error}"
        assert "Hello" in result.content or "hello" in result.content.lower()

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_claude_default_model(self, session_dir):
        """Test Claude with default model (no model specified)."""
        agent = ClaudeAgent({}, session_dir)
        result = agent.invoke("Respond with exactly: Hello World")

        assert result.success, f"Failed: {result.error}"
        assert "Hello" in result.content or "hello" in result.content.lower()


class TestGeminiModelSelection:
    """Test Gemini CLI with different model selections."""

    @pytest.mark.skipif(
        not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"),
        reason="GEMINI_API_KEY or GOOGLE_API_KEY not set"
    )
    def test_gemini_flash_hello_world(self, session_dir):
        """Test Gemini with 2.0 flash model."""
        agent = GeminiAgent({"model": "gemini-2.0-flash"}, session_dir)
        result = agent.invoke("Respond with exactly: Hello World")

        assert result.success, f"Failed: {result.error}"
        assert "Hello" in result.content or "hello" in result.content.lower()

    @pytest.mark.skipif(
        not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"),
        reason="GEMINI_API_KEY or GOOGLE_API_KEY not set"
    )
    def test_gemini_default_model(self, session_dir):
        """Test Gemini with default model (no model specified)."""
        agent = GeminiAgent({}, session_dir)
        result = agent.invoke("Respond with exactly: Hello World")

        assert result.success, f"Failed: {result.error}"
        assert "Hello" in result.content or "hello" in result.content.lower()


class TestCodexModelSelection:
    """Test Codex CLI with different model selections."""

    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    def test_codex_o4_mini_hello_world(self, session_dir):
        """Test Codex with o4-mini model."""
        agent = CodexAgent({"model": "o4-mini"}, session_dir)
        result = agent.invoke("Respond with exactly: Hello World")

        assert result.success, f"Failed: {result.error}"
        assert "Hello" in result.content or "hello" in result.content.lower()

    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    def test_codex_default_model(self, session_dir):
        """Test Codex with default model (no model specified)."""
        agent = CodexAgent({}, session_dir)
        result = agent.invoke("Respond with exactly: Hello World")

        assert result.success, f"Failed: {result.error}"
        assert "Hello" in result.content or "hello" in result.content.lower()
