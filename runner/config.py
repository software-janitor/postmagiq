"""Centralized configuration for the workflow orchestrator."""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# =============================================================================
# PostgreSQL Database (Primary - Market Upgrade)
# =============================================================================

# PostgreSQL connection URL
# Default points to PostgreSQL directly on port 5434
# Use DATABASE_URL env var to point to PgBouncer (6434) in production
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://orchestrator:orchestrator_dev@localhost:5434/orchestrator",
)

# Redis connection URL for caching
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# =============================================================================
# Workflow runtime paths
# =============================================================================

# Working directory for workflow runs
# Default: workflow/data/ in project directory (persistent)
WORKING_DIR = os.environ.get(
    "WORKFLOW_WORKING_DIR", str(PROJECT_ROOT / "workflow" / "data")
)

# =============================================================================
# Agent Mode Configuration (Phase 0A - API-Based Agents)
# =============================================================================

# Agent invocation mode: "cli" (subprocess) or "api" (SDK)
# CLI mode uses claude/gemini/codex CLI tools via subprocess
# API mode uses official SDKs (anthropic, openai, google-generativeai)
AGENT_MODE = os.environ.get("AGENT_MODE", "cli")

# API Keys for SDK-based agents (required when AGENT_MODE="api")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# =============================================================================
# Developer Mode (Debug Visibility)
# =============================================================================

# Enable dev mode to broadcast full LLM messages via WebSocket
# and write detailed logs to workflow/runs/{run_id}/dev_logs/
DEV_MODE = os.environ.get("POSTMAGIQ_DEV_MODE", "false").lower() == "true"

# =============================================================================
# Workflow Configuration (Phase 11 - Dynamic Workflow Config)
# =============================================================================

# Directory containing workflow configs
WORKFLOW_CONFIGS_DIR = PROJECT_ROOT / "workflows" / "configs"

# Default config path
DEFAULT_CONFIG_PATH = WORKFLOW_CONFIGS_DIR / "claude.yaml"


def resolve_workflow_config(config: str) -> Path:
    """Resolve a config name or path to an absolute path.

    Args:
        config: Either a config name (e.g., 'groq-production') or a path

    Returns:
        Path to the workflow config file

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    # If it looks like a path (contains / or ends with .yaml/.yml), use as-is
    if "/" in config or config.endswith((".yaml", ".yml")):
        config_path = Path(config)
        if not config_path.is_absolute():
            config_path = PROJECT_ROOT / config_path
    else:
        # It's a named config - look in workflows/configs/
        config_path = WORKFLOW_CONFIGS_DIR / f"{config}.yaml"

    if not config_path.exists():
        # Check for common alternatives
        alternatives = []
        if WORKFLOW_CONFIGS_DIR.exists():
            alternatives = [f.stem for f in WORKFLOW_CONFIGS_DIR.glob("*.yaml")]

        if alternatives:
            raise FileNotFoundError(
                f"Config not found: {config}\n"
                f"Available configs: {', '.join(sorted(alternatives))}"
            )
        else:
            raise FileNotFoundError(f"Config not found: {config_path}")

    return config_path


def list_workflow_configs() -> list[dict]:
    """List all available workflow configs.

    Returns:
        List of dicts with name, path, and enabled status
    """
    import yaml

    configs = []
    registry_path = PROJECT_ROOT / "workflows" / "registry.yaml"

    if registry_path.exists():
        with open(registry_path) as f:
            registry = yaml.safe_load(f)
            for name, meta in registry.get("workflows", {}).items():
                config_path = WORKFLOW_CONFIGS_DIR / meta.get(
                    "config_file", ""
                ).replace("configs/", "")
                configs.append(
                    {
                        "name": name,
                        "display_name": meta.get("name", name),
                        "description": meta.get("description", ""),
                        "environment": meta.get("environment", "production"),
                        "enabled": meta.get("enabled", True),
                        "path": str(config_path) if config_path.exists() else None,
                    }
                )
    else:
        # Fallback: list files in configs directory
        if WORKFLOW_CONFIGS_DIR.exists():
            for config_file in WORKFLOW_CONFIGS_DIR.glob("*.yaml"):
                configs.append(
                    {
                        "name": config_file.stem,
                        "display_name": config_file.stem,
                        "description": "",
                        "environment": "unknown",
                        "enabled": True,
                        "path": str(config_file),
                    }
                )

    return configs
