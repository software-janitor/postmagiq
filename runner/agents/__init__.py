"""Agent implementations and factory.

This module provides both CLI-based agents (subprocess invocation) and
API-based agents (SDK invocation). The create_agent factory automatically
selects the appropriate agent type based on AGENT_MODE configuration.

Usage:
    from runner.agents import create_agent

    # Creates CLI or API agent based on AGENT_MODE config
    agent = create_agent("claude", {"model": "sonnet"})

    # Explicitly specify mode
    agent = create_agent("claude", {"model": "sonnet"}, mode="api")
"""

from runner.agents.base import BaseAgent
from runner.agents.cli_base import CLIAgent

# CLI agents (subprocess-based) - always available
from runner.agents.claude import ClaudeAgent
from runner.agents.gemini import GeminiAgent
from runner.agents.codex import CodexAgent
from runner.agents.ollama import OllamaAgent

# API agents (SDK-based) - optional, require SDK dependencies
# These imports are wrapped in try/except to allow the package to work
# even without the SDK dependencies installed (for CLI-only mode)
APIAgent = None
ClaudeAPIAgent = None
OpenAIAPIAgent = None
GeminiAPIAgent = None

try:
    from runner.agents.api_base import APIAgent
except ImportError:
    pass

try:
    from runner.agents.claude_api import ClaudeAPIAgent
except ImportError:
    pass

try:
    from runner.agents.openai_api import OpenAIAPIAgent
except ImportError:
    pass

try:
    from runner.agents.gemini_api import GeminiAPIAgent
except ImportError:
    pass

GroqAPIAgent = None

try:
    from runner.agents.groq_api import GroqAPIAgent
except ImportError:
    pass

# Factory function (must be imported after agent classes are defined)
from runner.agents.factory import create_agent, get_available_agents  # noqa: E402

# Legacy registry for backwards compatibility
AGENT_REGISTRY = {
    "claude": ClaudeAgent,
    "gemini": GeminiAgent,
    "codex": CodexAgent,
    "gpt-5.2": CodexAgent,
    "ollama": OllamaAgent,
}

__all__ = [
    # Base classes
    "BaseAgent",
    "CLIAgent",
    "APIAgent",
    # CLI agents
    "ClaudeAgent",
    "GeminiAgent",
    "CodexAgent",
    "OllamaAgent",
    # API agents
    "ClaudeAPIAgent",
    "OpenAIAPIAgent",
    "GeminiAPIAgent",
    "GroqAPIAgent",
    # Factory
    "create_agent",
    "get_available_agents",
    # Legacy
    "AGENT_REGISTRY",
]
