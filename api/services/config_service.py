"""Service for workflow configuration management."""

import os
from pathlib import Path
from typing import Optional

import yaml


def get_default_config_path() -> str:
    """Get config path based on LLM_PROVIDER environment variable."""
    provider = os.environ.get("LLM_PROVIDER", "cli")
    config_map = {
        "groq": "workflow_config.groq.yaml",
        "ollama": "workflow_config.ollama.yaml",
        "cli": "workflow_config.yaml",  # Original CLI agents (claude, gemini, gpt)
    }
    return config_map.get(provider, "workflow_config.yaml")


class ConfigService:
    """Service for reading and validating workflow config."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = get_default_config_path()
        self.config_path = Path(config_path)

    def get_config(self) -> dict:
        """Get current workflow configuration."""
        if not self.config_path.exists():
            return {}
        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def get_config_yaml(self) -> str:
        """Get config as YAML string."""
        if not self.config_path.exists():
            return ""
        return self.config_path.read_text()

    def save_config(self, config_yaml: str) -> None:
        """Save config from YAML string."""
        # Validate it parses
        yaml.safe_load(config_yaml)
        self.config_path.write_text(config_yaml)

    def validate_config(self, config_yaml: str) -> tuple[bool, list[str], list[str]]:
        """Validate config YAML. Returns (valid, errors, warnings)."""
        errors = []
        warnings = []

        try:
            config = yaml.safe_load(config_yaml)
        except yaml.YAMLError as e:
            return False, [f"YAML parse error: {e}"], []

        if not config:
            return False, ["Config is empty"], []

        # Check required sections
        if "states" not in config:
            errors.append("Missing required section: states")

        states = config.get("states", {})

        # Validate state machine
        initial_states = []
        terminal_states = []

        for name, state in states.items():
            state_type = state.get("type")
            if not state_type:
                errors.append(f"State '{name}' missing type")
                continue

            valid_types = [
                "initial",
                "fan-out",
                "single",
                "orchestrator-task",
                "human-approval",
                "terminal",
            ]
            if state_type not in valid_types:
                errors.append(f"State '{name}' has invalid type: {state_type}")

            if state_type == "initial":
                initial_states.append(name)
            elif state_type == "terminal":
                terminal_states.append(name)

            # Check transitions exist
            if state_type not in ["initial", "terminal"]:
                transitions = state.get("transitions", {})
                next_state = state.get("next")
                if not transitions and not next_state:
                    warnings.append(f"State '{name}' has no transitions defined")

                # Verify transition targets exist
                all_targets = list(transitions.values()) if transitions else []
                if next_state:
                    all_targets.append(next_state)
                for target in all_targets:
                    if target not in states:
                        errors.append(
                            f"State '{name}' transitions to unknown state: {target}"
                        )

            # Check fan-out has agents
            if state_type == "fan-out":
                if not state.get("agents"):
                    errors.append(f"Fan-out state '{name}' missing agents list")

        if not initial_states:
            errors.append("No initial state defined")
        elif len(initial_states) > 1:
            warnings.append(f"Multiple initial states: {initial_states}")

        if not terminal_states:
            warnings.append("No terminal states defined")

        return len(errors) == 0, errors, warnings

    def get_agents(self) -> list[dict]:
        """Get list of available agents from config."""
        config = self.get_config()
        agents = config.get("agents", {})
        return [
            {"name": name, "enabled": agent.get("enabled", True), **agent}
            for name, agent in agents.items()
        ]

    def get_personas(self) -> list[dict]:
        """Get list of available personas from config."""
        config = self.get_config()
        personas = config.get("personas", {})
        result = []
        for name, path in personas.items():
            result.append({"name": name, "path": path})
        return result

    def get_workflow_states(self) -> list[dict]:
        """Get workflow states with their configuration for the UI."""
        config = self.get_config()
        states = config.get("states", {})
        result = []
        for name, state in states.items():
            state_info = {
                "id": name,
                "type": state.get("type"),
                "description": state.get("description", ""),
            }
            # Include agents for fan-out states
            if state.get("type") == "fan-out":
                state_info["agents"] = state.get("agents", [])
            # Include single agent for single/orchestrator-task states
            elif state.get("type") in ("single", "orchestrator-task"):
                agent = state.get("agent")
                if agent:
                    state_info["agents"] = [agent]
            result.append(state_info)
        return result
