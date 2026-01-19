"""Centralized configuration for the workflow orchestrator."""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# =============================================================================
# PostgreSQL Database (Primary - Market Upgrade)
# =============================================================================

# PostgreSQL connection URL
# Default points to PgBouncer on port 6432 for connection pooling
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://orchestrator:orchestrator_dev@localhost:6433/orchestrator"
)

# Redis connection URL for caching
REDIS_URL = os.environ.get(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

# =============================================================================
# Workflow runtime paths
# =============================================================================

# Working directory for workflow runs
# Default: workflow/data/ in project directory (persistent)
WORKING_DIR = os.environ.get(
    "WORKFLOW_WORKING_DIR",
    str(PROJECT_ROOT / "workflow" / "data")
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
