"""Tests for OllamaAgent."""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import requests

from runner.agents.ollama import OllamaAgent, MODEL_TIERS
from runner.models import TokenUsage


class TestOllamaModelTiers:
    """Tests for GPU-based model tier selection."""

    def test_tier_cpu_config(self):
        """CPU tier has minimal models."""
        tier = MODEL_TIERS["tier_cpu"]
        assert tier["vram_range"] == (0, 6)
        assert "phi3" in tier["models"]["writer"]  # phi3:mini for CPU
        assert tier["max_context"] == 4096

    def test_tier_8gb_config(self):
        """8GB tier has 8B models."""
        tier = MODEL_TIERS["tier_8gb"]
        assert tier["vram_range"] == (6, 10)
        assert "8b" in tier["models"]["writer"]

    def test_tier_48gb_config(self):
        """48GB tier supports 70B models."""
        tier = MODEL_TIERS["tier_48gb"]
        assert tier["vram_range"] == (40, 100)
        assert "70b" in tier["models"]["writer"]
        assert tier["max_context"] == 131072


class TestOllamaAgent:
    """Tests for OllamaAgent class."""

    @pytest.fixture
    def ollama_config(self):
        """Basic Ollama agent config."""
        return {
            "name": "ollama",
            "type": "ollama",
            "model": "llama3.3:70b",
            "timeout": 300,
        }

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_init_with_config(self, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """Agent initializes correctly with config."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        assert agent.model == "llama3.3:70b"
        assert agent.timeout == 300
        assert agent.tier == "tier_48gb"

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_model_from_config(self, mock_session, mock_tier, mock_gpu, tmp_path):
        """Model from config is used directly."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        config = {"model": "llama3.1:8b", "timeout": 60}
        agent = OllamaAgent(config, session_dir=str(tmp_path))

        assert agent.model == "llama3.1:8b"

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_custom_model_passes_through(self, mock_session, mock_tier, mock_gpu, tmp_path):
        """Custom models pass through without modification."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        config = {"model": "custom:latest", "timeout": 60}
        agent = OllamaAgent(config, session_dir=str(tmp_path))

        assert agent.model == "custom:latest"

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_get_model_for_persona(self, mock_session, mock_tier, mock_gpu, tmp_path):
        """Persona-based model selection works."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent({"model": "llama-70b"}, session_dir=str(tmp_path))

        # Writer tier gets the writer model
        writer_model = agent.get_model_for_persona("writer", "writer")
        assert writer_model == MODEL_TIERS["tier_48gb"]["models"]["writer"]

        # Coder tier gets the coder model
        coder_model = agent.get_model_for_persona("coder", "coder")
        assert coder_model == MODEL_TIERS["tier_48gb"]["models"]["coder"]

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_cost_is_zero(self, mock_session, mock_tier, mock_gpu, tmp_path):
        """Local Ollama is free."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=24, name="RTX 3090")
        mock_tier.return_value = "tier_24gb"

        agent = OllamaAgent({"model": "qwen-32b"}, session_dir=str(tmp_path))

        assert agent.cost_per_1k["input"] == 0.0
        assert agent.cost_per_1k["output"] == 0.0

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.post")
    @patch("runner.agents.ollama.requests.get")
    def test_invoke_success(self, mock_get, mock_post, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """Successful invocation returns AgentResult."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        # Mock list_models response
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:70b"}]}
        )

        # Mock chat response
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "message": {"content": "Test response"},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
            raise_for_status=lambda: None,
        )

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))
        result = agent.invoke("Test prompt")

        assert result.success is True
        assert result.content == "Test response"
        assert result.tokens.input_tokens == 100
        assert result.tokens.output_tokens == 50
        assert result.cost_usd == 0.0  # Local = free

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.post")
    @patch("runner.agents.ollama.requests.get")
    def test_invoke_timeout(self, mock_get, mock_post, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """Timeout returns failed AgentResult."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:70b"}]}
        )

        mock_post.side_effect = requests.exceptions.Timeout("Timeout")

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))
        result = agent.invoke("Test prompt")

        assert result.success is False
        assert "timed out" in result.error.lower()

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.get")
    def test_list_models(self, mock_get, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """list_models returns available model names."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "models": [
                    {"name": "llama3.3:70b"},
                    {"name": "qwen3:32b"},
                    {"name": "mixtral:8x22b"},
                ]
            },
            raise_for_status=lambda: None,
        )

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))
        models = agent.list_models()

        assert "llama3.3:70b" in models
        assert "qwen3:32b" in models
        assert len(models) == 3

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_session_type(self, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """Ollama uses file-based sessions."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        assert agent.session_type == "file"
        assert agent.supports_native_session() is False

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_get_gpu_info(self, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """get_gpu_info returns detection results."""
        from runner.agents.gpu_detect import GPUInfo
        mock_gpu.return_value = GPUInfo(
            vendor="nvidia",
            vram_gb=48.5,
            name="RTX 4090"
        )
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))
        info = agent.get_gpu_info()

        assert info["vendor"] == "nvidia"
        assert info["vram_gb"] == 48.5
        assert info["name"] == "RTX 4090"
        assert info["tier"] == "tier_48gb"

    @patch.dict("os.environ", {"OLLAMA_HOST": "http://192.168.1.100:11434"})
    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_custom_host_from_env(self, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """OLLAMA_HOST env var is respected."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        assert agent.host == "http://192.168.1.100:11434"


class TestOllamaJsonMode:
    """Tests for JSON mode detection and API formatting."""

    @pytest.fixture
    def ollama_config(self):
        """Basic Ollama agent config."""
        return {"model": "llama3.3:70b", "timeout": 300}

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_json_mode_detected_for_auditor_persona(self, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """JSON mode is enabled when prompt contains Auditor Persona."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        prompt = """# Auditor Persona

You are a quality gate auditor...

## Input Files
content here"""

        assert agent._should_use_json_mode(prompt) is True

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_json_mode_detected_for_json_output_instruction(self, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """JSON mode is enabled when prompt says 'Return ONLY valid JSON'."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        prompt = """Some persona instructions.

Return ONLY valid JSON. Do not wrap in markdown.

## Input Files
content"""

        assert agent._should_use_json_mode(prompt) is True

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_json_mode_detected_for_decision_field(self, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """JSON mode is enabled when prompt contains decision field example."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        prompt = """Instructions with example:
{"score": 8, "decision": "proceed", "feedback": "Good"}
"""

        assert agent._should_use_json_mode(prompt) is True

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_json_mode_not_detected_for_writer(self, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """JSON mode is NOT enabled for writer persona (prose output)."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        prompt = """# Writer Persona

You are a LinkedIn post writer. Write engaging prose.

## Input Files
story content here"""

        assert agent._should_use_json_mode(prompt) is False

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.post")
    @patch("runner.agents.ollama.requests.get")
    def test_json_format_sent_to_api_when_detected(self, mock_get, mock_post, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """format: 'json' is sent to Ollama API when JSON mode detected."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:70b"}]}
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "message": {"content": '{"score": 8, "decision": "proceed"}'},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
            raise_for_status=lambda: None,
        )

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        # Prompt that triggers JSON mode
        prompt = """# Auditor Persona
Return ONLY valid JSON.
## Input Files
content"""

        agent.invoke(prompt)

        # Check that format: json was in the request
        call_args = mock_post.call_args
        request_body = call_args[1]["json"]
        assert request_body.get("format") == "json"

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.post")
    @patch("runner.agents.ollama.requests.get")
    def test_json_format_not_sent_for_prose(self, mock_get, mock_post, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """format: 'json' is NOT sent for prose output prompts."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:70b"}]}
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "message": {"content": "A beautifully written post..."},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
            raise_for_status=lambda: None,
        )

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        # Writer prompt - no JSON mode
        prompt = """# Writer Persona
Write engaging LinkedIn posts.
## Input Files
story content"""

        agent.invoke(prompt)

        # Check that format was NOT in the request
        call_args = mock_post.call_args
        request_body = call_args[1]["json"]
        assert "format" not in request_body

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.post")
    @patch("runner.agents.ollama.requests.get")
    def test_explicit_json_mode_override(self, mock_get, mock_post, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """Explicit json_mode=True overrides auto-detection."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:70b"}]}
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "message": {"content": '{"data": "value"}'},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
            raise_for_status=lambda: None,
        )

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        # Simple prompt that wouldn't trigger auto-detection
        prompt = "Generate some data"

        agent.invoke(prompt, json_mode=True)

        call_args = mock_post.call_args
        request_body = call_args[1]["json"]
        assert request_body.get("format") == "json"


class TestOllamaMessageSplitting:
    """Tests for system/user message splitting."""

    @pytest.fixture
    def ollama_config(self):
        """Basic Ollama agent config."""
        return {"model": "llama3.3:70b", "timeout": 300}

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.post")
    @patch("runner.agents.ollama.requests.get")
    def test_prompt_split_at_input_files(self, mock_get, mock_post, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """Prompt is split into system and user messages at '## Input Files'."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:70b"}]}
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "message": {"content": "Response"},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
            raise_for_status=lambda: None,
        )

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        prompt = """# Writer Persona

You are a LinkedIn post writer.

## Input Files

File content here"""

        agent.invoke(prompt, json_mode=False)

        call_args = mock_post.call_args
        messages = call_args[1]["json"]["messages"]

        # Should have system + user messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "# Writer Persona" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "## Input Files" in messages[1]["content"]

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.post")
    @patch("runner.agents.ollama.requests.get")
    def test_prompt_split_at_context(self, mock_get, mock_post, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """Prompt is split at '## Context' if no Input Files marker."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:70b"}]}
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "message": {"content": "Response"},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
            raise_for_status=lambda: None,
        )

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        prompt = """# Persona Instructions

Do something useful.

## Context

Previous context here"""

        agent.invoke(prompt, json_mode=False)

        call_args = mock_post.call_args
        messages = call_args[1]["json"]["messages"]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "# Persona Instructions" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "## Context" in messages[1]["content"]

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    @patch("runner.agents.ollama.requests.post")
    @patch("runner.agents.ollama.requests.get")
    def test_simple_prompt_no_split(self, mock_get, mock_post, mock_session, mock_tier, mock_gpu, ollama_config, tmp_path):
        """Simple prompts without markers are sent as single user message."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:70b"}]}
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "message": {"content": "Response"},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
            raise_for_status=lambda: None,
        )

        agent = OllamaAgent(ollama_config, session_dir=str(tmp_path))

        prompt = "Just a simple question without any structure"

        agent.invoke(prompt, json_mode=False)

        call_args = mock_post.call_args
        messages = call_args[1]["json"]["messages"]

        # Should have just one user message
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == prompt
