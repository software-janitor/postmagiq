"""Smoke test fixtures and configuration."""

import os
import pytest


def pytest_configure(config):
    """Set up environment before any tests run."""
    # Set required env vars for smoke tests
    if not os.environ.get("JWT_SECRET"):
        os.environ["JWT_SECRET"] = "smoke-test-secret"
    if not os.environ.get("LLM_PROVIDER"):
        os.environ["LLM_PROVIDER"] = "ollama"
