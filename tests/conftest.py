"""Shared fixtures and mock agents for testing."""

import pytest
from typing import Optional

from runner.models import AgentResult, TokenUsage


class MockAgent:
    """Mock agent for testing without API calls."""

    def __init__(self, responses: list[str], tokens_per_call: int = 100):
        self.responses = responses
        self.tokens_per_call = tokens_per_call
        self.call_count = 0
        self.prompts_received: list[str] = []
        self.name = "mock"
        self.context_window = 100000
        self.cost_per_1k = {"input": 0.001, "output": 0.002}

    def invoke(self, prompt: str, input_files: Optional[list[str]] = None) -> AgentResult:
        """Return next canned response."""
        self.prompts_received.append(prompt)
        response = self.responses[self.call_count % len(self.responses)] if self.responses else ""
        self.call_count += 1

        return AgentResult(
            success=True,
            content=response,
            tokens=TokenUsage(
                input_tokens=len(prompt.split()) * 2,
                output_tokens=self.tokens_per_call,
            ),
            duration_s=0.1,
        )

    def invoke_with_session(
        self, session_id: str, prompt: str, input_files: Optional[list[str]] = None
    ) -> AgentResult:
        """Same as invoke but with session tracking."""
        result = self.invoke(prompt, input_files)
        result.session_id = session_id
        return result

    def reset(self):
        """Reset for new test."""
        self.call_count = 0
        self.prompts_received = []


class FailingAgent(MockAgent):
    """Agent that fails after N successful calls."""

    def __init__(self, responses: list[str], fail_after: int = 1):
        super().__init__(responses)
        self.fail_after = fail_after

    def invoke(self, prompt: str, input_files: Optional[list[str]] = None) -> AgentResult:
        if self.call_count >= self.fail_after:
            self.call_count += 1
            return AgentResult(
                success=False,
                content="",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
                error="Simulated failure",
            )
        return super().invoke(prompt, input_files)


class TimeoutAgent(MockAgent):
    """Agent that simulates timeout."""

    def __init__(self, delay_seconds: float = 0.1):
        super().__init__([])
        self.delay = delay_seconds

    def invoke(self, prompt: str, input_files: Optional[list[str]] = None) -> AgentResult:
        import time

        time.sleep(self.delay)
        return AgentResult(
            success=False,
            content="",
            tokens=TokenUsage(input_tokens=0, output_tokens=0),
            error="Timeout",
        )


@pytest.fixture
def mock_agent():
    """Provide a fresh MockAgent."""
    return MockAgent(["Test response 1", "Test response 2"])


@pytest.fixture
def failing_agent():
    """Provide a FailingAgent that fails immediately."""
    return FailingAgent([], fail_after=0)


@pytest.fixture
def mock_agents():
    """Provide a dict of mock agents for fan-out testing."""
    return {
        "claude": MockAgent(["Draft from Claude: The GPU hit 94°C..."]),
        "gemini": MockAgent(["Draft from Gemini: I wanted to keep..."]),
        "codex": MockAgent(["Draft from Codex: Self-hosting seemed..."]),
    }
