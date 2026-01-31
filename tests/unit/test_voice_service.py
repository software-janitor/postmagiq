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
