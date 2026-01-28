"""Tests for GroqAPIAgent."""

import pytest
from unittest.mock import MagicMock, patch

from runner.agents.groq_api import GroqAPIAgent
from runner.models import TokenUsage


class TestGroqAPIAgent:
    """Tests for GroqAPIAgent class."""

    @pytest.fixture
    def groq_config(self):
        """Basic Groq agent config."""
        return {
            "name": "groq-70b",
            "type": "api",
            "model": "llama-70b",
            "max_tokens": 4096,
        }

    @patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
    @patch("runner.agents.groq_api.Groq")
    def test_init_with_config(self, mock_groq, groq_config):
        """Agent initializes correctly with config."""
        agent = GroqAPIAgent(groq_config)

        assert agent.model == "llama-70b"
        assert agent.max_tokens == 4096
        mock_groq.assert_called_once_with(api_key="test_key")

    @patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
    @patch("runner.agents.groq_api.Groq")
    def test_model_alias_resolution(self, mock_groq, groq_config):
        """Model aliases resolve to actual model IDs."""
        agent = GroqAPIAgent(groq_config)

        # Test various aliases
        assert agent.MODEL_MAP["llama-70b"] == "llama-3.3-70b-versatile"
        assert agent.MODEL_MAP["llama-8b"] == "llama-3.1-8b-instant"
        assert agent.MODEL_MAP["mixtral"] == "mixtral-8x7b-32768"
        assert agent.MODEL_MAP["llama4-scout"] == "meta-llama/llama-4-scout-17b-16e-instruct"
        assert agent.MODEL_MAP["llama4-maverick"] == "meta-llama/llama-4-maverick-17b-128e-instruct"

    @patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
    @patch("runner.agents.groq_api.Groq")
    def test_resolve_model_id(self, mock_groq, groq_config):
        """_resolve_model_id converts aliases."""
        agent = GroqAPIAgent(groq_config)

        # Known alias
        agent.model = "llama-70b"
        assert agent._resolve_model_id() == "llama-3.3-70b-versatile"

        # Unknown model passes through
        agent.model = "custom-model"
        assert agent._resolve_model_id() == "custom-model"

    @patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
    @patch("runner.agents.groq_api.Groq")
    def test_invoke_success(self, mock_groq, groq_config):
        """Successful API call returns AgentResult."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        agent = GroqAPIAgent(groq_config)
        result = agent.invoke("Test prompt")

        assert result.success is True
        assert result.content == "Test response"
        assert result.tokens.input_tokens == 100
        assert result.tokens.output_tokens == 50

    @patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
    @patch("runner.agents.groq_api.Groq")
    def test_invoke_with_system_prompt(self, mock_groq, groq_config):
        """System prompt is prepended to messages."""
        groq_config["system_prompt"] = "You are a helpful assistant."

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 25

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        agent = GroqAPIAgent(groq_config)
        agent.invoke("Hello")

        # Verify system prompt was included
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."


class TestGroqModelPricing:
    """Tests for Groq model pricing configuration."""

    @patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
    @patch("runner.agents.groq_api.Groq")
    def test_model_pricing_defined(self, mock_groq):
        """All mapped models have pricing defined."""
        agent = GroqAPIAgent({"model": "llama-70b"})

        for alias, model_id in agent.MODEL_MAP.items():
            # Whisper models don't have token pricing
            if "whisper" in alias or "whisper" in model_id:
                continue

            assert model_id in agent.MODEL_PRICING, f"Missing pricing for {model_id}"
            pricing = agent.MODEL_PRICING[model_id]
            assert "input" in pricing
            assert "output" in pricing
            assert pricing["input"] > 0
            assert pricing["output"] > 0


class TestGroqTranscription:
    """Tests for Groq audio transcription."""

    @patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
    @patch("runner.agents.groq_api.Groq")
    def test_transcribe_returns_expected_format(self, mock_groq):
        """Transcribe returns dict with expected keys."""
        mock_response = MagicMock()
        mock_response.text = "Hello world"
        mock_response.duration = 10.5
        mock_response.language = "en"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        agent = GroqAPIAgent({"model": "llama-70b"})
        result = agent.transcribe(MagicMock(), model="whisper-large-v3")

        assert "text" in result
        assert "duration" in result
        assert "tokens" in result
        assert result["text"] == "Hello world"
        assert result["duration"] == 10.5

    @patch.dict("os.environ", {"GROQ_API_KEY": "test_key"})
    @patch("runner.agents.groq_api.Groq")
    def test_transcribe_minimum_one_token(self, mock_groq):
        """Short audio should still return at least 1 token."""
        mock_response = MagicMock()
        mock_response.text = "Hi"
        mock_response.duration = 0.5  # Very short
        mock_response.language = "en"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        agent = GroqAPIAgent({"model": "llama-70b"})
        result = agent.transcribe(MagicMock())

        assert result["tokens"] >= 1
