"""Agent factory with CLI/API mode selection.

This module provides the create_agent function that creates agent instances
based on the configured AGENT_MODE (cli or api).

Usage:
    from runner.agents.factory import create_agent

    # Will use CLI or API based on AGENT_MODE config
    agent = create_agent("claude", {"model": "sonnet"})
"""

from runner.agents.base import BaseAgent
from runner.config import AGENT_MODE

# CLI agent registry (existing agents)
CLI_AGENT_REGISTRY: dict[str, type] = {}

# API agent registry (new SDK-based agents)
API_AGENT_REGISTRY: dict[str, type] = {}


def _lazy_load_registries():
    """Lazily load agent registries to avoid import cycles."""
    global CLI_AGENT_REGISTRY, API_AGENT_REGISTRY

    if not CLI_AGENT_REGISTRY:
        from runner.agents.claude import ClaudeAgent
        from runner.agents.gemini import GeminiAgent
        from runner.agents.codex import CodexAgent
        from runner.agents.ollama import OllamaAgent

        CLI_AGENT_REGISTRY.update({
            "claude": ClaudeAgent,
            "gemini": GeminiAgent,
            "codex": CodexAgent,
            "gpt-5.2": CodexAgent,
            "ollama": OllamaAgent,
        })

    # API agents are optional - only load if SDK dependencies are available
    if not API_AGENT_REGISTRY:
        try:
            from runner.agents.claude_api import ClaudeAPIAgent
            API_AGENT_REGISTRY["claude"] = ClaudeAPIAgent
        except ImportError:
            pass

        try:
            from runner.agents.openai_api import OpenAIAPIAgent
            API_AGENT_REGISTRY["openai"] = OpenAIAPIAgent
            API_AGENT_REGISTRY["gpt"] = OpenAIAPIAgent  # Alias
        except ImportError:
            pass

        try:
            from runner.agents.gemini_api import GeminiAPIAgent
            API_AGENT_REGISTRY["gemini"] = GeminiAPIAgent
        except ImportError:
            pass
        # Note: ollama and codex don't have API equivalents yet


def _get_base_agent(name: str, registry: dict) -> str | None:
    """Get base agent type from a variant name.

    Examples:
        claude-sonnet -> claude
        gemini-3-pro -> gemini
        claude -> claude
        gpt4o -> openai (in API mode)
    """
    # Direct match
    if name in registry:
        return name

    # Check for prefix match (e.g., claude-sonnet -> claude)
    for base in registry:
        if name.startswith(f"{base}-"):
            return base

    # Special handling for GPT models in API mode
    if name.startswith("gpt") and "openai" in registry:
        return "openai"

    return None


def create_agent(
    name: str,
    config: dict,
    session_dir: str = "workflow/sessions",
    mode: str | None = None
) -> BaseAgent:
    """Factory to create agent instances.

    Creates either a CLI-based agent (subprocess) or API-based agent (SDK)
    depending on the AGENT_MODE configuration or explicit mode parameter.

    Args:
        name: Agent name (claude, gemini, openai) or variant (claude-sonnet)
        config: Agent configuration dict including 'model', 'timeout', etc.
        session_dir: Directory for session files (CLI agents only)
        mode: Override AGENT_MODE config. One of 'cli', 'api', or None (use config)

    Returns:
        Agent instance (either CLIAgent or APIAgent subclass)

    Raises:
        ValueError: If agent name is not recognized for the selected mode
    """
    _lazy_load_registries()

    effective_mode = mode or AGENT_MODE

    if effective_mode == "api":
        return _create_api_agent(name, config)
    else:
        return _create_cli_agent(name, config, session_dir)


def _create_cli_agent(name: str, config: dict, session_dir: str) -> BaseAgent:
    """Create a CLI-based agent."""
    base_agent = _get_base_agent(name, CLI_AGENT_REGISTRY)
    if base_agent is None:
        raise ValueError(
            f"Unknown CLI agent: {name}. "
            f"Available: {list(CLI_AGENT_REGISTRY.keys())}"
        )

    agent_config = {**config, "name": name}
    return CLI_AGENT_REGISTRY[base_agent](agent_config, session_dir)


def _create_api_agent(name: str, config: dict) -> BaseAgent:
    """Create an API-based agent."""
    base_agent = _get_base_agent(name, API_AGENT_REGISTRY)
    if base_agent is None:
        # Fall back to CLI agent if no API equivalent exists
        # (e.g., ollama, codex)
        return _create_cli_agent(name, config, "workflow/sessions")

    agent_config = {**config, "name": name}
    return API_AGENT_REGISTRY[base_agent](agent_config)


def get_available_agents(mode: str | None = None) -> list[str]:
    """Get list of available agent names for the given mode.

    Args:
        mode: 'cli', 'api', or None (use AGENT_MODE config)

    Returns:
        List of available agent names
    """
    _lazy_load_registries()
    effective_mode = mode or AGENT_MODE

    if effective_mode == "api":
        return list(API_AGENT_REGISTRY.keys())
    else:
        return list(CLI_AGENT_REGISTRY.keys())
