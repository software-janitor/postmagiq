"""Integration tests for OllamaAgent with real Ollama server.

These tests require:
- Ollama server running at OLLAMA_HOST (default: http://192.168.165.62:11434)
- llama3.3:70b model available

Run with: pytest tests/integration/test_ollama_integration.py -v
"""

import os
import json
import pytest
import requests

from runner.agents.ollama import OllamaAgent

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://192.168.165.62:11434")
MODEL = "llama3.3:70b"


def is_ollama_available() -> bool:
    """Check if Ollama server is reachable and has required model."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code != 200:
            return False
        models = [m["name"] for m in response.json().get("models", [])]
        return MODEL in models
    except Exception:
        return False


skip_if_no_ollama = pytest.mark.skipif(
    not is_ollama_available(),
    reason=f"Ollama server not available or {MODEL} not found"
)


@skip_if_no_ollama
class TestOllamaIntegration:
    """Integration tests for OllamaAgent."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create OllamaAgent configured for test server."""
        config = {
            "model": MODEL,
            "timeout": 120,
        }
        # Set OLLAMA_HOST env for agent
        os.environ["OLLAMA_HOST"] = OLLAMA_HOST
        return OllamaAgent(config, session_dir=str(tmp_path))

    def test_simple_prompt(self, agent):
        """Agent can respond to a simple prompt."""
        result = agent.invoke("What is 2 + 2? Reply with just the number.")

        assert result.success is True
        assert "4" in result.content
        assert result.tokens.input_tokens > 0
        assert result.tokens.output_tokens > 0
        assert result.cost_usd == 0.0  # Local = free

    def test_json_mode_returns_valid_json(self, agent):
        """JSON mode forces valid JSON output."""
        prompt = """Return a JSON object with these fields:
- name: string
- age: number
- active: boolean

Example: {"name": "John", "age": 30, "active": true}"""

        result = agent.invoke(prompt, json_mode=True)

        assert result.success is True

        # Should be valid JSON
        try:
            data = json.loads(result.content)
            assert "name" in data
            assert "age" in data
            assert "active" in data
        except json.JSONDecodeError:
            pytest.fail(f"Response is not valid JSON: {result.content[:200]}")

    def test_auditor_persona_returns_json(self, agent):
        """Auditor persona with JSON instructions returns valid JSON."""
        prompt = """# Auditor Persona

You are a quality auditor. Evaluate the text and return your assessment.

Return ONLY valid JSON with these fields:
- score: integer 1-10
- decision: one of "proceed", "retry", or "halt"
- feedback: string with your feedback

## Input Files

The quick brown fox jumps over the lazy dog. This is a test sentence."""

        result = agent.invoke(prompt)  # Auto-detect JSON mode

        assert result.success is True

        # Should be valid JSON with required fields
        try:
            data = json.loads(result.content)
            assert "score" in data
            assert "decision" in data
            assert data["decision"] in ["proceed", "retry", "halt"]
            assert "feedback" in data
        except json.JSONDecodeError:
            pytest.fail(f"Auditor response is not valid JSON: {result.content[:200]}")

    def test_writer_persona_returns_prose(self, agent):
        """Writer persona returns prose, not JSON."""
        prompt = """# Writer Persona

You are a LinkedIn post writer. Write engaging, conversational content.

## Input Files

Topic: The importance of taking breaks during work."""

        result = agent.invoke(prompt, json_mode=False)

        assert result.success is True
        assert len(result.content) > 50  # Should have substantial prose

        # Should NOT be JSON
        try:
            json.loads(result.content)
            # If it parses as JSON, that's unexpected for prose
            assert False, "Writer should return prose, not JSON"
        except json.JSONDecodeError:
            pass  # Expected - prose is not JSON

    def test_system_user_message_split(self, agent):
        """Prompt is correctly split into system/user messages."""
        # This tests that the model receives proper instruction following
        prompt = """# Strict Rules

You MUST respond with exactly the word "CONFIRMED" and nothing else.
Do not add any explanation or punctuation.

## Input Files

Please confirm you understand the rules."""

        result = agent.invoke(prompt, json_mode=False)

        assert result.success is True
        # Model should follow system instructions
        assert "CONFIRMED" in result.content.upper()


@skip_if_no_ollama
class TestOllamaAuditResult:
    """Test that Ollama returns proper AuditResult format for workflow."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create OllamaAgent configured for test server."""
        config = {"model": MODEL, "timeout": 120}
        os.environ["OLLAMA_HOST"] = OLLAMA_HOST
        return OllamaAgent(config, session_dir=str(tmp_path))

    def test_audit_decision_proceed(self, agent):
        """Auditor returns proceed for good content."""
        prompt = """# Auditor Persona

Evaluate if this LinkedIn post is ready to publish.

Return ONLY valid JSON:
{"score": <1-10>, "decision": "<proceed|retry|halt>", "feedback": "<your feedback>"}

## Input Files

I learned something valuable today: taking short breaks actually makes you more productive. After implementing 25-minute focus sessions with 5-minute breaks, my output increased by 30%. Sometimes slowing down helps you speed up."""

        result = agent.invoke(prompt)

        assert result.success is True
        data = json.loads(result.content)
        assert data["score"] >= 6  # Should be decent quality
        assert data["decision"] in ["proceed", "retry", "halt"]

    def test_audit_decision_retry(self, agent):
        """Auditor returns retry for content needing improvement."""
        prompt = """# Auditor Persona

Evaluate if this LinkedIn post is ready to publish.
If it's too short or vague, return decision: "retry".

Return ONLY valid JSON:
{"score": <1-10>, "decision": "<proceed|retry|halt>", "feedback": "<your feedback>"}

## Input Files

Work is good."""

        result = agent.invoke(prompt)

        assert result.success is True
        data = json.loads(result.content)
        assert data["score"] <= 5  # Should be low quality
        assert data["decision"] == "retry"  # Should request retry
        assert len(data["feedback"]) > 10  # Should have feedback
