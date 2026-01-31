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
            "signature_phrases",
            "storytelling_style",
            "emotional_register",
            "summary",
        ]

        for field in required_fields:
            assert f'"{field}"' in VOICE_ANALYSIS_PROMPT, f"Missing field: {field}"
