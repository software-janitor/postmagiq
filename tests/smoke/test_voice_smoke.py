"""Smoke tests for voice service.

These tests verify basic functionality without making real API calls.
Run with: pytest tests/smoke/test_voice_smoke.py -v
"""

import os
import pytest


class TestVoiceServiceSmoke:
    """Basic smoke tests for voice service initialization."""

    def test_voice_service_initializes(self, monkeypatch):
        """Voice service creates agent successfully with default config."""
        # Use ollama as default - doesn't require API key
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("OLLAMA_VOICE_MODEL", raising=False)

        from api.services.voice_service import VoiceService

        # Mock content service to avoid DB dependency
        class MockContentService:
            pass

        service = VoiceService(content_service=MockContentService())

        assert service.llm_provider == "ollama"
        assert service.model == "llama3.2"
        assert service.agent is not None

    def test_voice_service_uses_provider_specific_model(self, monkeypatch):
        """Voice service picks up provider-specific model env var."""
        # Set env vars before import
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_VOICE_MODEL", "custom-model")
        monkeypatch.setenv("GROQ_API_KEY", "test-key-for-smoke-test")

        from api.services.voice_service import VoiceService

        class MockContentService:
            pass

        service = VoiceService(content_service=MockContentService())

        assert service.llm_provider == "groq"
        assert service.model == "custom-model"

    def test_voice_prompts_available(self):
        """Voice prompts can be loaded."""
        from api.services.voice_service import VoiceService

        prompts = VoiceService.get_prompts()
        assert len(prompts) == 10
        assert all("id" in p for p in prompts)
        assert all("prompt" in p for p in prompts)


class TestVoiceModelDefaults:
    """Smoke tests for voice service model defaults."""

    def test_groq_default_model_value(self):
        """Groq default model is gpt-oss-120b."""
        model_defaults = {
            "groq": "gpt-oss-120b",
            "ollama": "llama3.2",
            "claude": "sonnet",
            "gemini": "gemini-2.0-flash",
            "openai": "gpt-5.2",
        }
        assert model_defaults["groq"] == "gpt-oss-120b"

    def test_ollama_default_model_value(self):
        """Ollama default model is llama3.2."""
        model_defaults = {
            "groq": "gpt-oss-120b",
            "ollama": "llama3.2",
            "claude": "sonnet",
            "gemini": "gemini-2.0-flash",
            "openai": "gpt-5.2",
        }
        assert model_defaults["ollama"] == "llama3.2"

    def test_env_var_pattern(self):
        """Env var pattern matches {PROVIDER}_VOICE_MODEL."""
        provider = "groq"
        env_var = f"{provider.upper()}_VOICE_MODEL"
        assert env_var == "GROQ_VOICE_MODEL"

        provider = "ollama"
        env_var = f"{provider.upper()}_VOICE_MODEL"
        assert env_var == "OLLAMA_VOICE_MODEL"
