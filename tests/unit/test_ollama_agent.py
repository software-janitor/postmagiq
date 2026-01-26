"""Tests for OllamaAgent."""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import requests

from runner.agents.ollama import OllamaAgent, MODEL_MAP, MODEL_TIERS
from runner.models import TokenUsage


class TestOllamaModelMapping:
    """Tests for model alias mapping."""

    def test_llama4_aliases(self):
        """Llama 4 model aliases resolve correctly."""
        assert MODEL_MAP["llama4-scout"] == "llama4:scout"
        assert MODEL_MAP["llama4"] == "llama4:scout"

    def test_llama3_aliases(self):
        """Llama 3.x model aliases resolve correctly."""
        assert MODEL_MAP["llama-70b"] == "llama3.3:70b"
        assert MODEL_MAP["llama-8b"] == "llama3.1:8b"
        assert MODEL_MAP["llama3.3"] == "llama3.3:70b"

    def test_mixtral_aliases(self):
        """Mixtral model aliases resolve correctly."""
        assert MODEL_MAP["mixtral-8x22b"] == "mixtral:8x22b"
        assert MODEL_MAP["mixtral"] == "mixtral:8x22b"

    def test_qwen_aliases(self):
        """Qwen model aliases resolve correctly."""
        assert MODEL_MAP["qwen-32b"] == "qwen3:32b"
        assert MODEL_MAP["qwen3"] == "qwen3:32b"


class TestOllamaModelTiers:
    """Tests for GPU-based model tier selection."""

    def test_tier_cpu_config(self):
        """CPU tier has minimal models."""
        tier = MODEL_TIERS["tier_cpu"]
        assert tier["vram_range"] == (0, 6)
        assert "1b" in tier["models"]["writer"]
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
            "model": "llama-70b",
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

        assert agent.model == "llama3.3:70b"  # llama-70b alias resolved
        assert agent.timeout == 300
        assert agent.tier == "tier_48gb"

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_model_alias_resolution(self, mock_session, mock_tier, mock_gpu, tmp_path):
        """Model aliases are resolved during init."""
        mock_gpu.return_value = MagicMock(vendor="nvidia", vram_gb=48, name="RTX 4090")
        mock_tier.return_value = "tier_48gb"

        config = {"model": "llama4-scout", "timeout": 60}
        agent = OllamaAgent(config, session_dir=str(tmp_path))

        assert agent.model == "llama4:scout"

    @patch("runner.agents.ollama.detect_gpu")
    @patch("runner.agents.ollama.get_model_tier")
    @patch("runner.agents.ollama.FileBasedSessionManager")
    def test_unknown_model_passes_through(self, mock_session, mock_tier, mock_gpu, tmp_path):
        """Unknown models pass through without modification."""
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
