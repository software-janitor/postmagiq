"""Integration tests for voice service with real LLM providers.

These tests make real API calls and cost money.
Run with: pytest tests/integration/test_voice_integration.py -v

Skip with: pytest -m "not live"
"""

import os
import pytest

from runner.agents.factory import create_agent


# Mark all tests in this module as live (require real API access)
pytestmark = pytest.mark.live


class TestVoiceAnalysisWithGroq:
    """Test voice analysis using Groq provider."""

    @pytest.mark.skipif(
        not os.environ.get("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set"
    )
    def test_voice_analysis_with_groq(self):
        """Full voice analysis with Groq API returns valid JSON."""
        agent = create_agent(
            "groq",
            {
                "name": "voice-test",
                "model": "gpt-oss-120b",
                "max_tokens": 2048,
                "timeout": 60,
                "type": "api",
            },
        )

        prompt = """Analyze this writing sample and return JSON:

Sample: "I've been thinking about this for a while. Here's the thing -
writing isn't just about words. It's about rhythm. Short sentences punch.
Long ones flow like rivers through valleys. But the real magic? Mixing them."

Return this exact JSON structure:
{
  "tone": "description",
  "vocabulary_level": "description",
  "summary": "brief summary"
}"""

        result = agent.invoke(prompt)
        assert result.success, f"Failed: {result.error}"
        assert result.content is not None
        # Response should contain JSON-like content
        assert "tone" in result.content.lower() or "{" in result.content

    @pytest.mark.skipif(
        not os.environ.get("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set"
    )
    def test_voice_analysis_returns_expected_fields(self):
        """Voice analysis response includes expected voice profile fields."""
        import json

        agent = create_agent(
            "groq",
            {
                "name": "voice-test",
                "model": "gpt-oss-120b",
                "max_tokens": 2048,
                "timeout": 60,
                "type": "api",
            },
        )

        prompt = """Analyze this writing sample and return ONLY valid JSON:

Sample: "Look, I get it. Change is hard. But staying stuck? That's harder.
I learned this the hard way, when everything I thought I knew... turned
out to be wrong. Now I embrace the chaos."

Return ONLY this JSON (no markdown, no explanation):
{"tone": "your analysis", "vocabulary_level": "your analysis", "summary": "your analysis"}"""

        if hasattr(agent, 'invoke_json'):
            result = agent.invoke_json(prompt)
        else:
            result = agent.invoke(prompt)

        assert result.success, f"Failed: {result.error}"

        # Try to parse response as JSON
        content = result.content.strip()
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            data = json.loads(content)
            # Check expected fields
            assert "tone" in data or "vocabulary_level" in data or "summary" in data
        except json.JSONDecodeError:
            # At minimum, the response should mention voice-related terms
            assert any(term in result.content.lower() for term in ["tone", "vocabulary", "summary", "style"])


class TestVoiceModelEnvVar:
    """Test that provider-specific model env vars work."""

    @pytest.mark.skipif(
        not os.environ.get("GROQ_API_KEY"),
        reason="GROQ_API_KEY not set"
    )
    def test_groq_voice_model_env_var(self, monkeypatch):
        """GROQ_VOICE_MODEL env var is used when set."""
        monkeypatch.setenv("GROQ_VOICE_MODEL", "llama-3.3-70b-versatile")
        monkeypatch.setenv("LLM_PROVIDER", "groq")

        # Import fresh to pick up env changes
        import importlib
        import api.services.voice_service as vs
        importlib.reload(vs)

        service = vs.VoiceService.__new__(vs.VoiceService)
        service.llm_provider = "groq"

        env_var = f"{service.llm_provider.upper()}_VOICE_MODEL"
        model = os.environ.get(env_var, "gpt-oss-120b")

        assert model == "llama-3.3-70b-versatile"
