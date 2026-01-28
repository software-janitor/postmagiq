"""Tests for ConfigService and LLM_PROVIDER configuration."""

import os
import pytest
from unittest.mock import patch

from api.services.config_service import ConfigService, get_default_config_path


class TestGetDefaultConfigPath:
    """Tests for get_default_config_path function."""

    def test_default_is_cli(self):
        """Without LLM_PROVIDER, defaults to CLI config."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove LLM_PROVIDER if it exists
            os.environ.pop("LLM_PROVIDER", None)
            path = get_default_config_path()
            assert path == "workflow_config.yaml"

    def test_groq_provider(self):
        """LLM_PROVIDER=groq selects groq config."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq"}):
            path = get_default_config_path()
            assert path == "workflow_config.groq.yaml"

    def test_ollama_provider(self):
        """LLM_PROVIDER=ollama selects ollama config."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
            path = get_default_config_path()
            assert path == "workflow_config.ollama.yaml"

    def test_cli_provider(self):
        """LLM_PROVIDER=cli selects legacy config."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "cli"}):
            path = get_default_config_path()
            assert path == "workflow_config.yaml"

    def test_unknown_provider_falls_back_to_default(self):
        """Unknown provider falls back to default config."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}):
            path = get_default_config_path()
            assert path == "workflow_config.yaml"


class TestConfigService:
    """Tests for ConfigService class."""

    def test_init_with_explicit_path(self, tmp_path):
        """ConfigService accepts explicit config path."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("orchestrator:\n  agent: test\n")

        service = ConfigService(str(config_file))
        config = service.get_config()

        assert config["orchestrator"]["agent"] == "test"

    def test_get_config_returns_empty_for_missing_file(self, tmp_path):
        """Returns empty dict if config file doesn't exist."""
        service = ConfigService(str(tmp_path / "nonexistent.yaml"))
        config = service.get_config()
        assert config == {}

    def test_get_config_yaml(self, tmp_path):
        """get_config_yaml returns raw YAML string."""
        config_file = tmp_path / "test_config.yaml"
        config_content = "orchestrator:\n  agent: test\n"
        config_file.write_text(config_content)

        service = ConfigService(str(config_file))
        yaml_str = service.get_config_yaml()

        assert yaml_str == config_content

    def test_get_agents(self, tmp_path):
        """get_agents extracts agents from config."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
agents:
  groq-70b:
    type: api
    enabled: true
    model: llama-70b
  groq-8b:
    type: api
    enabled: false
    model: llama-8b
""")

        service = ConfigService(str(config_file))
        agents = service.get_agents()

        assert len(agents) == 2
        agent_names = [a["name"] for a in agents]
        assert "groq-70b" in agent_names
        assert "groq-8b" in agent_names

        groq_70b = next(a for a in agents if a["name"] == "groq-70b")
        assert groq_70b["enabled"] is True
        assert groq_70b["model"] == "llama-70b"

    def test_get_workflow_states(self, tmp_path):
        """get_workflow_states extracts states for UI."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
states:
  start:
    type: initial
    next: draft
  draft:
    type: fan-out
    description: "Generate drafts"
    agents: [agent1, agent2]
  complete:
    type: terminal
    description: "Done"
""")

        service = ConfigService(str(config_file))
        states = service.get_workflow_states()

        assert len(states) == 3

        start = next(s for s in states if s["id"] == "start")
        assert start["type"] == "initial"

        draft = next(s for s in states if s["id"] == "draft")
        assert draft["type"] == "fan-out"
        assert draft["agents"] == ["agent1", "agent2"]

        complete = next(s for s in states if s["id"] == "complete")
        assert complete["type"] == "terminal"


class TestConfigValidation:
    """Tests for config validation."""

    def test_validate_empty_config(self, tmp_path):
        """Empty config is invalid."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("")

        service = ConfigService(str(config_file))
        valid, errors, warnings = service.validate_config("")

        assert valid is False
        assert "Config is empty" in errors

    def test_validate_missing_states(self, tmp_path):
        """Config without states section is invalid."""
        service = ConfigService("/nonexistent")
        valid, errors, warnings = service.validate_config("orchestrator:\n  agent: test")

        assert valid is False
        assert any("states" in e for e in errors)

    def test_validate_invalid_yaml(self, tmp_path):
        """Invalid YAML returns parse error."""
        service = ConfigService("/nonexistent")
        valid, errors, warnings = service.validate_config("invalid: yaml: content:")

        assert valid is False
        assert any("YAML parse error" in e for e in errors)

    def test_validate_state_without_type(self, tmp_path):
        """State without type is invalid."""
        config = """
states:
  start:
    next: complete
  complete:
    type: terminal
"""
        service = ConfigService("/nonexistent")
        valid, errors, warnings = service.validate_config(config)

        assert valid is False
        assert any("'start' missing type" in e for e in errors)

    def test_validate_invalid_transition_target(self, tmp_path):
        """Transition to unknown state is invalid."""
        config = """
states:
  start:
    type: initial
    next: draft
  draft:
    type: single
    transitions:
      success: nonexistent
"""
        service = ConfigService("/nonexistent")
        valid, errors, warnings = service.validate_config(config)

        assert valid is False
        assert any("nonexistent" in e for e in errors)

    def test_validate_fan_out_without_agents(self, tmp_path):
        """Fan-out state without agents is invalid."""
        config = """
states:
  start:
    type: initial
    next: draft
  draft:
    type: fan-out
    transitions:
      success: complete
  complete:
    type: terminal
"""
        service = ConfigService("/nonexistent")
        valid, errors, warnings = service.validate_config(config)

        assert valid is False
        assert any("agents list" in e for e in errors)

    def test_validate_valid_config(self, tmp_path):
        """Valid config passes validation."""
        config = """
states:
  start:
    type: initial
    next: draft
  draft:
    type: single
    agent: groq
    transitions:
      success: complete
  complete:
    type: terminal
"""
        service = ConfigService("/nonexistent")
        valid, errors, warnings = service.validate_config(config)

        assert valid is True
        assert errors == []
