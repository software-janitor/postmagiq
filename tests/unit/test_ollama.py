"""Tests for Ollama agent and related components."""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from runner.agents.gpu_detect import GPUInfo, detect_gpu, get_model_tier, get_gpu_summary
from runner.agents.ollama import OllamaAgent, MODEL_TIERS
from runner.sessions.file_based import FileBasedSessionManager


class TestGPUDetection:
    """Tests for GPU detection module."""

    def test_get_model_tier_cpu(self):
        """Test tier selection for no GPU."""
        gpu = GPUInfo(vendor="none", vram_gb=0)
        assert get_model_tier(gpu) == "tier_cpu"

    def test_get_model_tier_low_vram(self):
        """Test tier selection for low VRAM."""
        gpu = GPUInfo(vendor="nvidia", vram_gb=4)
        assert get_model_tier(gpu) == "tier_cpu"

    def test_get_model_tier_8gb(self):
        """Test tier selection for 8GB VRAM."""
        gpu = GPUInfo(vendor="nvidia", vram_gb=8)
        assert get_model_tier(gpu) == "tier_8gb"

    def test_get_model_tier_16gb(self):
        """Test tier selection for 16GB VRAM."""
        gpu = GPUInfo(vendor="nvidia", vram_gb=16)
        assert get_model_tier(gpu) == "tier_16gb"

    def test_get_model_tier_24gb(self):
        """Test tier selection for 24GB VRAM."""
        gpu = GPUInfo(vendor="nvidia", vram_gb=24, name="RTX 3090")
        assert get_model_tier(gpu) == "tier_24gb"

    def test_get_model_tier_48gb(self):
        """Test tier selection for 48GB+ VRAM."""
        gpu = GPUInfo(vendor="nvidia", vram_gb=48)
        assert get_model_tier(gpu) == "tier_48gb"

    def test_get_model_tier_boundary_6gb(self):
        """Test tier boundary at 6GB."""
        gpu = GPUInfo(vendor="nvidia", vram_gb=6)
        assert get_model_tier(gpu) == "tier_8gb"

    def test_get_model_tier_boundary_12gb(self):
        """Test tier boundary at 12GB."""
        gpu = GPUInfo(vendor="nvidia", vram_gb=12)
        assert get_model_tier(gpu) == "tier_16gb"

    @patch("runner.agents.gpu_detect.subprocess.run")
    def test_detect_nvidia(self, mock_run):
        """Test NVIDIA GPU detection."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="GeForce RTX 3090, 24576"
        )
        gpu = detect_gpu()
        assert gpu.vendor == "nvidia"
        assert gpu.vram_gb == 24.0
        assert "3090" in gpu.name

    @patch("runner.agents.gpu_detect.subprocess.run")
    def test_detect_nvidia_timeout(self, mock_run):
        """Test NVIDIA detection timeout falls back gracefully."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("nvidia-smi", 5)
        gpu = detect_gpu()
        # Should fall back to no GPU
        assert gpu.vendor == "none"

    @patch("runner.agents.gpu_detect.subprocess.run")
    def test_detect_no_gpu(self, mock_run):
        """Test detection when no GPU available."""
        mock_run.side_effect = FileNotFoundError()
        gpu = detect_gpu()
        assert gpu.vendor == "none"
        assert gpu.vram_gb == 0.0

    def test_get_gpu_summary(self):
        """Test GPU summary output."""
        with patch("runner.agents.gpu_detect.detect_gpu") as mock:
            mock.return_value = GPUInfo(vendor="nvidia", vram_gb=24, name="RTX 3090")
            summary = get_gpu_summary()

            assert summary["vendor"] == "nvidia"
            assert summary["vram_gb"] == 24
            assert summary["tier"] == "tier_24gb"
            assert summary["has_gpu"] is True


class TestFileBasedSession:
    """Tests for file-based session manager."""

    def test_create_and_load_session(self, tmp_path):
        """Test creating and loading a session."""
        manager = FileBasedSessionManager(str(tmp_path))
        session = manager.create_session("test-session")

        assert session["session_id"] == "test-session"
        assert len(session["messages"]) == 0
        assert session["total_tokens"] == 0

        loaded = manager.load_session("test-session")
        assert loaded == session

    def test_add_message(self, tmp_path):
        """Test adding messages to session."""
        manager = FileBasedSessionManager(str(tmp_path))
        manager.create_session("test-session")

        manager.add_message("user", "Hello")
        manager.add_message("assistant", "Hi there")

        session = manager.load_session("test-session")
        assert len(session["messages"]) == 2
        assert session["messages"][0]["role"] == "user"
        assert session["messages"][1]["role"] == "assistant"

    def test_add_message_with_tokens(self, tmp_path):
        """Test adding message with token counts."""
        manager = FileBasedSessionManager(str(tmp_path))
        manager.create_session("test-session")

        manager.add_message("user", "Hello", {"input": 10, "output": 0, "total": 10})
        manager.add_message(
            "assistant", "Hi", {"input": 10, "output": 20, "total": 30}
        )

        session = manager.load_session("test-session")
        assert session["total_tokens"] == 40

    def test_trim_old_messages(self, tmp_path):
        """Test that old messages are trimmed."""
        manager = FileBasedSessionManager(str(tmp_path), max_messages=5)
        manager.create_session("test-session")

        for i in range(10):
            manager.add_message("user", f"Message {i}")

        session = manager.load_session("test-session")
        assert len(session["messages"]) == 5

    def test_system_messages_preserved_in_trim(self, tmp_path):
        """Test that system messages are preserved during trimming."""
        manager = FileBasedSessionManager(str(tmp_path), max_messages=5)
        manager.create_session("test-session")

        # Add a system message
        manager.add_system_message("You are a helpful assistant.")

        # Add many user messages
        for i in range(10):
            manager.add_message("user", f"Message {i}")

        session = manager.load_session("test-session")
        system_msgs = [m for m in session["messages"] if m["role"] == "system"]
        assert len(system_msgs) == 1

    def test_get_context_for_ollama(self, tmp_path):
        """Test getting context formatted for Ollama API."""
        manager = FileBasedSessionManager(str(tmp_path))
        manager.create_session("test-session")
        manager.add_message("user", "Hello")
        manager.add_message("assistant", "Hi")

        context = manager.get_context_for_ollama()
        assert len(context) == 2
        assert context[0] == {"role": "user", "content": "Hello"}
        assert context[1] == {"role": "assistant", "content": "Hi"}

    def test_clear_session(self, tmp_path):
        """Test clearing a session."""
        manager = FileBasedSessionManager(str(tmp_path))
        manager.create_session("test-session")
        manager.add_message("user", "Hello")

        manager.clear_session()

        assert manager.has_session() is False
        assert manager.load_session("test-session") is None

    def test_list_sessions(self, tmp_path):
        """Test listing all sessions."""
        manager = FileBasedSessionManager(str(tmp_path))
        manager.create_session("session-1")
        manager.create_session("session-2")
        manager.create_session("session-3")

        sessions = manager.list_sessions()
        assert len(sessions) == 3
        assert "session-1" in sessions
        assert "session-2" in sessions
        assert "session-3" in sessions

    def test_has_session(self, tmp_path):
        """Test has_session check."""
        manager = FileBasedSessionManager(str(tmp_path))
        assert manager.has_session() is False

        manager.create_session("test")
        assert manager.has_session() is True

    def test_add_message_without_session_fails(self, tmp_path):
        """Test that adding message without session raises error."""
        manager = FileBasedSessionManager(str(tmp_path))

        with pytest.raises(ValueError, match="No session loaded"):
            manager.add_message("user", "Hello")


class TestOllamaAgent:
    """Tests for OllamaAgent class."""

    @pytest.fixture
    def mock_gpu(self):
        """Mock GPU detection."""
        with patch("runner.agents.ollama.detect_gpu") as mock:
            mock.return_value = GPUInfo(vendor="nvidia", vram_gb=24)
            yield mock

    def test_tier_selection(self, mock_gpu, tmp_path):
        """Test that agent selects correct tier."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        assert agent.tier == "tier_24gb"
        assert agent.context_window == MODEL_TIERS["tier_24gb"]["max_context"]

    def test_model_from_config_override(self, mock_gpu, tmp_path):
        """Test that model can be overridden via config."""
        agent = OllamaAgent(
            {"name": "ollama", "model": "custom:model"}, session_dir=str(tmp_path)
        )

        assert agent.model == "custom:model"

    def test_get_model_for_persona_writer(self, mock_gpu, tmp_path):
        """Test model selection for writer tier."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        model = agent.get_model_for_persona("any_persona", model_tier="writer")
        assert model == MODEL_TIERS["tier_24gb"]["models"]["writer"]

    def test_get_model_for_persona_auditor(self, mock_gpu, tmp_path):
        """Test model selection for auditor tier."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        model = agent.get_model_for_persona("any_persona", model_tier="auditor")
        assert model == MODEL_TIERS["tier_24gb"]["models"]["auditor"]

    def test_get_model_for_persona_coder(self, mock_gpu, tmp_path):
        """Test model selection for coder tier."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        model = agent.get_model_for_persona("any_persona", model_tier="coder")
        assert model == MODEL_TIERS["tier_24gb"]["models"]["coder"]

    def test_get_model_for_persona_defaults_to_writer(self, mock_gpu, tmp_path):
        """Test that model selection defaults to writer when no tier provided."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        # Without model_tier, should default to writer
        model = agent.get_model_for_persona("any_persona")
        assert model == MODEL_TIERS["tier_24gb"]["models"]["writer"]

    def test_session_type_is_file(self, mock_gpu, tmp_path):
        """Test that session type is 'file'."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))
        assert agent.session_type == "file"

    def test_no_native_session(self, mock_gpu, tmp_path):
        """Test that native session is not supported."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))
        assert agent.supports_native_session() is False

    def test_get_gpu_info(self, mock_gpu, tmp_path):
        """Test GPU info retrieval."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        info = agent.get_gpu_info()
        assert info["vendor"] == "nvidia"
        assert info["vram_gb"] == 24
        assert info["tier"] == "tier_24gb"

    def test_set_model_for_persona(self, mock_gpu, tmp_path):
        """Test setting model based on persona."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        agent.set_model_for_persona("auditor")
        assert agent.model == MODEL_TIERS["tier_24gb"]["models"]["auditor"]

    def test_get_model_with_explicit_tier(self, mock_gpu, tmp_path):
        """Test model selection with explicit model_tier from database."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        # Explicit tier should override persona name matching
        model = agent.get_model_for_persona("custom_persona", model_tier="auditor")
        assert model == MODEL_TIERS["tier_24gb"]["models"]["auditor"]

        model = agent.get_model_for_persona("random_name", model_tier="coder")
        assert model == MODEL_TIERS["tier_24gb"]["models"]["coder"]

    def test_explicit_tier_overrides_name_match(self, mock_gpu, tmp_path):
        """Test that explicit tier takes precedence over persona name."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        # Even if persona name contains "auditor", explicit tier wins
        model = agent.get_model_for_persona("auditor_persona", model_tier="writer")
        assert model == MODEL_TIERS["tier_24gb"]["models"]["writer"]

    def test_invalid_tier_falls_back_to_name_match(self, mock_gpu, tmp_path):
        """Test fallback to name matching when tier is invalid."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        # Invalid tier should fall back to string matching
        model = agent.get_model_for_persona("auditor_persona", model_tier="invalid")
        assert model == MODEL_TIERS["tier_24gb"]["models"]["auditor"]

    def test_set_model_with_explicit_tier(self, mock_gpu, tmp_path):
        """Test set_model_for_persona with explicit tier."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))

        agent.set_model_for_persona("custom_persona", model_tier="coder")
        assert agent.model == MODEL_TIERS["tier_24gb"]["models"]["coder"]

    def test_cost_is_zero(self, mock_gpu, tmp_path):
        """Test that cost is always zero for local models."""
        agent = OllamaAgent({"name": "ollama"}, session_dir=str(tmp_path))
        assert agent.cost_per_1k["input"] == 0.0
        assert agent.cost_per_1k["output"] == 0.0


class TestModelTiers:
    """Tests for MODEL_TIERS configuration."""

    def test_all_tiers_have_required_fields(self):
        """Test that all tiers have required configuration."""
        required_fields = ["vram_range", "models", "fallback", "max_context"]

        for tier_name, tier_config in MODEL_TIERS.items():
            for field in required_fields:
                assert (
                    field in tier_config
                ), f"Tier {tier_name} missing field {field}"

    def test_all_tiers_have_model_types(self):
        """Test that all tiers have writer, auditor, coder models."""
        required_models = ["writer", "auditor", "coder"]

        for tier_name, tier_config in MODEL_TIERS.items():
            models = tier_config["models"]
            for model_type in required_models:
                assert (
                    model_type in models
                ), f"Tier {tier_name} missing model type {model_type}"

    def test_tier_context_windows_increase(self):
        """Test that context windows increase with tiers."""
        tiers = ["tier_cpu", "tier_8gb", "tier_16gb", "tier_24gb", "tier_48gb"]

        prev_context = 0
        for tier in tiers:
            context = MODEL_TIERS[tier]["max_context"]
            assert context > prev_context, f"Tier {tier} context should be > {prev_context}"
            prev_context = context
