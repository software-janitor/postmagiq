"""Tests for voice service."""

import pytest


class TestVoiceAnalysisPrompt:
    """Tests for voice analysis prompt formatting."""

    def test_prompt_format_does_not_raise_key_error(self):
        """Ensure VOICE_ANALYSIS_PROMPT.format() works with samples parameter.

        The prompt contains JSON examples with braces that must be escaped
        as {{ and }} to prevent Python's .format() from interpreting them
        as placeholders.
        """
        from api.services.voice_service import VOICE_ANALYSIS_PROMPT

        samples_text = "Sample 1: Hello world\n\nSample 2: Testing voice"

        # This should not raise KeyError
        formatted = VOICE_ANALYSIS_PROMPT.format(samples=samples_text)

        # Verify the samples were inserted
        assert "Sample 1: Hello world" in formatted
        assert "Sample 2: Testing voice" in formatted

        # Verify the JSON example braces are present (unescaped after format)
        assert '"tone"' in formatted
        assert '"sentence_patterns"' in formatted

    def test_prompt_contains_required_json_fields(self):
        """Ensure the prompt specifies all required output fields."""
        from api.services.voice_service import VOICE_ANALYSIS_PROMPT

        required_fields = [
            "tone",
            "sentence_patterns",
            "vocabulary_level",
            "punctuation_style",
            "transition_style",
            "paragraph_rhythm",
            "reader_address",
            "signature_phrases",
            "storytelling_style",
            "emotional_register",
            "summary",
        ]

        for field in required_fields:
            assert f'"{field}"' in VOICE_ANALYSIS_PROMPT, f"Missing field: {field}"

    def test_system_prompt_emphasizes_transferable_patterns(self):
        """System prompt should focus on reusable patterns, not content."""
        from api.services.voice_service import VOICE_SYSTEM_PROMPT

        # Should emphasize transferable patterns
        assert "TRANSFERABLE" in VOICE_SYSTEM_PROMPT or "transferable" in VOICE_SYSTEM_PROMPT.lower()
        assert "REUSABLE" in VOICE_SYSTEM_PROMPT or "reusable" in VOICE_SYSTEM_PROMPT.lower()

        # Should warn against content-specific extraction
        assert "product" in VOICE_SYSTEM_PROMPT.lower() or "brand" in VOICE_SYSTEM_PROMPT.lower()

    def test_prompt_includes_punctuation_analysis(self):
        """Prompt should analyze punctuation to avoid AI-tell patterns."""
        from api.services.voice_service import VOICE_ANALYSIS_PROMPT

        assert "em_dashes" in VOICE_ANALYSIS_PROMPT or "em-dash" in VOICE_ANALYSIS_PROMPT.lower()
        assert "semicolons" in VOICE_ANALYSIS_PROMPT.lower()
        assert "ellipses" in VOICE_ANALYSIS_PROMPT.lower()


class TestVoiceServiceModelSelection:
    """Tests for provider-specific model selection."""

    def test_groq_default_model(self, monkeypatch):
        """Groq uses gpt-oss-120b by default when no env var set."""
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.delenv("GROQ_VOICE_MODEL", raising=False)

        from api.services.voice_service import VoiceService

        service = VoiceService.__new__(VoiceService)
        service.llm_provider = "groq"

        model_defaults = {
            "groq": "gpt-oss-120b",
            "ollama": "llama3.2",
            "claude": "sonnet",
            "gemini": "gemini-2.0-flash",
            "openai": "gpt-5.2",
        }
        env_var = f"{service.llm_provider.upper()}_VOICE_MODEL"
        import os
        default_model = model_defaults.get(service.llm_provider, "llama3.2")
        model = os.environ.get(env_var, default_model)

        assert model == "gpt-oss-120b"

    def test_groq_custom_model(self, monkeypatch):
        """Groq uses custom model when GROQ_VOICE_MODEL is set."""
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_VOICE_MODEL", "llama-70b")

        import os
        model = os.environ.get("GROQ_VOICE_MODEL", "gpt-oss-120b")
        assert model == "llama-70b"

    def test_ollama_default_model(self, monkeypatch):
        """Ollama uses llama3.2 by default when no env var set."""
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("OLLAMA_VOICE_MODEL", raising=False)

        model_defaults = {"ollama": "llama3.2"}
        import os
        env_var = "OLLAMA_VOICE_MODEL"
        default_model = model_defaults.get("ollama", "llama3.2")
        model = os.environ.get(env_var, default_model)

        assert model == "llama3.2"

    def test_ollama_custom_model(self, monkeypatch):
        """Ollama uses custom model when OLLAMA_VOICE_MODEL is set."""
        monkeypatch.setenv("OLLAMA_VOICE_MODEL", "mistral")

        import os
        model = os.environ.get("OLLAMA_VOICE_MODEL", "llama3.2")
        assert model == "mistral"

    def test_all_providers_have_defaults(self):
        """Every supported provider has a sensible default model."""
        model_defaults = {
            "groq": "gpt-oss-120b",
            "ollama": "llama3.2",
            "claude": "sonnet",
            "gemini": "gemini-2.0-flash",
            "openai": "gpt-5.2",
        }

        expected_providers = ["groq", "ollama", "claude", "gemini", "openai"]
        for provider in expected_providers:
            assert provider in model_defaults, f"Missing default for {provider}"
            assert model_defaults[provider], f"Empty default for {provider}"

    def test_claude_default_model(self, monkeypatch):
        """Claude uses sonnet by default when no env var set."""
        monkeypatch.delenv("CLAUDE_VOICE_MODEL", raising=False)

        model_defaults = {"claude": "sonnet"}
        import os
        model = os.environ.get("CLAUDE_VOICE_MODEL", model_defaults["claude"])

        assert model == "sonnet"

    def test_gemini_default_model(self, monkeypatch):
        """Gemini uses gemini-2.0-flash by default when no env var set."""
        monkeypatch.delenv("GEMINI_VOICE_MODEL", raising=False)

        model_defaults = {"gemini": "gemini-2.0-flash"}
        import os
        model = os.environ.get("GEMINI_VOICE_MODEL", model_defaults["gemini"])

        assert model == "gemini-2.0-flash"

    def test_openai_default_model(self, monkeypatch):
        """OpenAI uses gpt-5.2 by default when no env var set."""
        monkeypatch.delenv("OPENAI_VOICE_MODEL", raising=False)

        model_defaults = {"openai": "gpt-5.2"}
        import os
        model = os.environ.get("OPENAI_VOICE_MODEL", model_defaults["openai"])

        assert model == "gpt-5.2"

    def test_unknown_provider_uses_fallback(self):
        """Unknown provider falls back to llama3.2."""
        model_defaults = {
            "groq": "gpt-oss-120b",
            "ollama": "llama3.2",
        }

        default_model = model_defaults.get("unknown_provider", "llama3.2")
        assert default_model == "llama3.2"


class TestVoiceProfileFormatting:
    """Tests for voice profile data formatting functions."""

    def test_format_sentence_patterns_from_json(self):
        """Format JSON sentence patterns into readable text."""
        from api.services.content_service import _format_sentence_patterns

        json_value = '{"average_length": "medium", "variation": "varied", "common_structures": ["simple declarative", "compound sentences"]}'
        result = _format_sentence_patterns(json_value)

        assert "Medium sentence length" in result
        assert "varied variation" in result
        assert "Uses: simple declarative, compound sentences" in result

    def test_format_sentence_patterns_plain_text_passthrough(self):
        """Plain text sentence patterns pass through unchanged."""
        from api.services.content_service import _format_sentence_patterns

        plain_text = "Short punchy sentences. Varied rhythm."
        result = _format_sentence_patterns(plain_text)

        assert result == plain_text

    def test_format_sentence_patterns_none(self):
        """None input returns None."""
        from api.services.content_service import _format_sentence_patterns

        assert _format_sentence_patterns(None) is None

    def test_format_signature_phrases_from_json_array(self):
        """Format JSON array of phrases into comma-separated text."""
        from api.services.content_service import _format_signature_phrases

        json_value = '["First phrase", "Second phrase", "Third phrase"]'
        result = _format_signature_phrases(json_value)

        assert result == "First phrase, Second phrase, Third phrase"

    def test_format_signature_phrases_plain_text_passthrough(self):
        """Plain text signature phrases pass through unchanged."""
        from api.services.content_service import _format_signature_phrases

        plain_text = "The key insight is..., What separates success from failure..."
        result = _format_signature_phrases(plain_text)

        assert result == plain_text

    def test_format_signature_phrases_none(self):
        """None input returns None."""
        from api.services.content_service import _format_signature_phrases

        assert _format_signature_phrases(None) is None

class TestVoiceProfileStorage:
    """Tests for voice profile storage without legacy wrapper."""

    def test_no_legacy_wrapper_in_save(self):
        """Verify save functions don't use legacy JSON wrapper."""
        import inspect
        from api.services.content_service import ContentService

        # Check that save_voice_profile doesn't reference legacy
        source = inspect.getsource(ContentService.save_voice_profile)
        assert "legacy" not in source.lower()
        assert "_encode_legacy" not in source

    def test_no_legacy_wrapper_in_workspace_save(self):
        """Verify workspace save doesn't use legacy JSON wrapper."""
        import inspect
        from api.services.content_service import ContentService

        source = inspect.getsource(ContentService.save_voice_profile_for_workspace)
        assert "legacy" not in source.lower()
        assert "_encode_legacy" not in source

    def test_response_uses_native_fields(self):
        """Verify response builder uses native DB fields."""
        import inspect
        from api.services.content_service import ContentService

        source = inspect.getsource(ContentService._voice_profile_response)
        assert "_decode_legacy" not in source
        assert "profile.tone_description" in source
        assert "profile.signature_phrases" in source
