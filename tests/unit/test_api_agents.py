"""Unit tests for API-based agents.

These tests use mocked API responses to test agent behavior
without making actual API calls.

Skipped if SDK dependencies (anthropic, openai, google-generativeai) are not installed.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Skip entire module if SDK dependencies aren't available
pytest.importorskip("anthropic", reason="anthropic SDK not installed")

from runner.agents.api_base import APIAgent, RateLimitError
from runner.agents.claude_api import ClaudeAPIAgent
from runner.agents.openai_api import OpenAIAPIAgent
from runner.agents.gemini_api import GeminiAPIAgent
from runner.agents.groq_api import GroqAPIAgent
from runner.agents.factory import create_agent, get_available_agents
from runner.models import TokenUsage


# =============================================================================
# APIAgent Base Class Tests
# =============================================================================

class TestAPIAgentBase:
    """Tests for APIAgent base class functionality."""

    def test_build_prompt_no_files(self):
        """Test prompt building without input files."""
        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            result = agent._build_prompt("Hello", None)
            assert result == "Hello"

    def test_build_prompt_with_files(self, tmp_path):
        """Test prompt building with input files."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("File content here")

        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            result = agent._build_prompt("Hello", [str(test_file)])
            assert "Hello" in result
            assert "File content here" in result
            assert "## File:" in result

    def test_build_prompt_missing_file(self):
        """Test prompt building with non-existent file."""
        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            result = agent._build_prompt("Hello", ["/nonexistent/file.txt"])
            assert result == "Hello"

    def test_clear_session(self):
        """Test session clearing."""
        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            agent.messages = [{"role": "user", "content": "test"}]
            agent.clear_session()
            assert agent.messages == []

    def test_session_type(self):
        """Test session type is memory."""
        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            assert agent.session_type == "memory"

    def test_supports_native_session(self):
        """Test that API agents don't support native sessions."""
        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            assert agent.supports_native_session() is False


# =============================================================================
# ClaudeAPIAgent Tests
# =============================================================================

class TestClaudeAPIAgent:
    """Tests for ClaudeAPIAgent."""

    def test_model_resolution_alias(self):
        """Test model alias resolution."""
        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            assert agent.model_id == "claude-sonnet-4-20250514"

    def test_model_resolution_full_name(self):
        """Test full model name passes through."""
        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "claude-3-opus-20240229"})
            assert agent.model_id == "claude-3-opus-20240229"

    def test_invoke_success(self):
        """Test successful invocation."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Response text")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20

        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            agent.client = MagicMock()
            agent.client.messages.create.return_value = mock_response

            result = agent.invoke("Hello")

            assert result.success is True
            assert result.content == "Response text"
            assert result.tokens.input_tokens == 10
            assert result.tokens.output_tokens == 20

    def test_invoke_with_session(self):
        """Test invocation with session maintains history."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Response 1")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20

        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            agent.client = MagicMock()
            agent.client.messages.create.return_value = mock_response

            result1 = agent.invoke_with_session("session-1", "Hello")
            assert result1.success is True
            assert len(agent.messages) == 2  # user + assistant

            # Second call should include history
            mock_response.content = [MagicMock(type="text", text="Response 2")]
            result2 = agent.invoke_with_session("session-1", "Follow up")
            assert result2.success is True
            assert len(agent.messages) == 4


# =============================================================================
# OpenAIAPIAgent Tests
# =============================================================================

class TestOpenAIAPIAgent:
    """Tests for OpenAIAPIAgent."""

    def test_model_resolution_alias(self):
        """Test model alias resolution."""
        with patch.object(OpenAIAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = OpenAIAPIAgent({"model": "gpt4o"})
            assert agent.model_id == "gpt-4o"

    def test_invoke_success(self):
        """Test successful invocation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response text"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        with patch.object(OpenAIAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = OpenAIAPIAgent({"model": "gpt4o"})
            agent.client = MagicMock()
            agent.client.chat.completions.create.return_value = mock_response

            result = agent.invoke("Hello")

            assert result.success is True
            assert result.content == "Response text"
            assert result.tokens.input_tokens == 10
            assert result.tokens.output_tokens == 20


# =============================================================================
# GeminiAPIAgent Tests
# =============================================================================

class TestGeminiAPIAgent:
    """Tests for GeminiAPIAgent."""

    def test_model_resolution_alias(self):
        """Test model alias resolution."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                with patch.object(GeminiAPIAgent, '_get_api_key_from_env', return_value='test-key'):
                    agent = GeminiAPIAgent({"model": "flash"})
                    assert agent.model_id == "gemini-1.5-flash"


# =============================================================================
# GroqAPIAgent Tests
# =============================================================================

class TestGroqAPIAgent:
    """Tests for GroqAPIAgent."""

    def test_model_resolution_alias(self):
        """Test model alias resolution."""
        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "llama-70b"})
            assert agent.model_id == "llama-3.3-70b-versatile"

    def test_model_resolution_direct(self):
        """Test direct model name passes through."""
        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "llama-3.3-70b-versatile"})
            assert agent.model_id == "llama-3.3-70b-versatile"

    def test_invoke_success(self):
        """Test successful invocation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "llama-70b"})
            agent.client = MagicMock()
            agent.client.chat.completions.create.return_value = mock_response
            result = agent.invoke("Hello")
            assert result.success is True
            assert result.content == "Response"
            assert result.tokens.input_tokens == 10
            assert result.tokens.output_tokens == 20

    def test_transcribe_returns_tokens(self):
        """Test transcription returns tokens."""
        mock_response = MagicMock()
        mock_response.text = "Transcribed text"
        mock_response.duration = 60  # 1 minute

        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "whisper"})
            agent.client = MagicMock()
            agent.client.audio.transcriptions.create.return_value = mock_response

            # Must pass file-like object, not string
            mock_file = MagicMock()
            result = agent.transcribe(mock_file)

            assert result["text"] == "Transcribed text"
            assert result["duration"] == 60
            # 1 minute = 1/60 hour, tokens = max(1, int(1/60 * 11.1)) = 1
            assert result["tokens"] >= 1

    def test_transcribe_short_audio_minimum_token(self):
        """Ensure short audio files return at least 1 token."""
        mock_response = MagicMock()
        mock_response.text = "Hi"
        mock_response.duration = 1  # 1 second

        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "whisper"})
            agent.client = MagicMock()
            agent.client.audio.transcriptions.create.return_value = mock_response

            mock_file = MagicMock()
            result = agent.transcribe(mock_file)

            # Even 1 second should return at least 1 token
            assert result["tokens"] == 1

    def test_rate_limit_error(self):
        """Test that Groq rate limit errors are converted."""
        from groq import RateLimitError as GroqRateLimitError

        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "llama-70b"})
            agent.client = MagicMock()
            # Create mock error with required parameters
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_error = GroqRateLimitError(
                message="Rate limited",
                response=mock_response,
                body=None
            )
            agent.client.chat.completions.create.side_effect = mock_error

            with pytest.raises(RateLimitError):
                agent._call_api([{"role": "user", "content": "test"}])


# =============================================================================
# Factory Tests
# =============================================================================

class TestAgentFactory:
    """Tests for agent factory."""

    def test_get_available_agents_cli(self):
        """Test getting available CLI agents."""
        agents = get_available_agents("cli")
        assert "claude" in agents
        assert "gemini" in agents
        assert "ollama" in agents

    def test_get_available_agents_api(self):
        """Test getting available API agents."""
        agents = get_available_agents("api")
        assert "claude" in agents
        assert "openai" in agents
        assert "gemini" in agents
        assert "groq" in agents

    def test_create_cli_agent(self):
        """Test creating a CLI agent."""
        agent = create_agent("claude", {"model": "sonnet"}, mode="cli")
        from runner.agents.claude import ClaudeAgent
        assert isinstance(agent, ClaudeAgent)

    def test_create_api_agent(self):
        """Test creating an API agent."""
        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = create_agent("claude", {"model": "sonnet"}, mode="api")
            assert isinstance(agent, ClaudeAPIAgent)

    def test_create_unknown_agent_raises(self):
        """Test that unknown agent raises ValueError."""
        with pytest.raises(ValueError, match="Unknown"):
            create_agent("unknown_agent", {}, mode="cli")

    def test_gpt_alias_resolves_to_openai(self):
        """Test that gpt* models resolve to OpenAI agent."""
        with patch.object(OpenAIAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = create_agent("gpt4o", {"model": "gpt4o"}, mode="api")
            assert isinstance(agent, OpenAIAPIAgent)

    def test_create_groq_agent(self):
        """Test creating a Groq API agent."""
        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = create_agent("groq", {"model": "llama-70b"}, mode="api")
            assert isinstance(agent, GroqAPIAgent)

    def test_groq_variant_resolves_to_groq(self):
        """Test that groq-* models resolve to Groq agent."""
        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = create_agent("groq-llama-70b", {"model": "llama-70b"}, mode="api")
            assert isinstance(agent, GroqAPIAgent)


# =============================================================================
# Rate Limit Retry Tests
# =============================================================================

class TestRateLimitRetry:
    """Tests for rate limit retry logic."""

    def test_retry_on_rate_limit(self):
        """Test that rate limit errors trigger retries."""
        call_count = 0

        def mock_call_api(messages):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limited")
            return "Success", TokenUsage(input_tokens=10, output_tokens=20)

        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            agent._call_api = mock_call_api
            agent.RETRY_BACKOFF_BASE = 0.01  # Speed up test

            result = agent.invoke("Hello")

            assert result.success is True
            assert call_count == 3

    def test_max_retries_exhausted(self):
        """Test that max retries leads to failure."""
        def mock_call_api(messages):
            raise RateLimitError("Rate limited")

        with patch.object(ClaudeAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = ClaudeAPIAgent({"model": "sonnet"})
            agent._call_api = mock_call_api
            agent.MAX_RETRIES = 2
            agent.RETRY_BACKOFF_BASE = 0.01

            result = agent.invoke("Hello")

            assert result.success is False
            assert "Rate limited" in result.error
