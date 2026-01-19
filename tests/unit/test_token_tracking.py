"""Tests for token tracking and cost calculation."""

import pytest
from runner.models import TokenUsage
from runner.metrics import (
    TokenTracker,
    SessionTokens,
    calculate_cost,
    get_default_cost,
    format_cost,
    estimate_run_cost,
)


class TestCostCalculation:
    def test_calculate_cost(self):
        tokens = TokenUsage(input_tokens=1000, output_tokens=500)
        cost_per_1k = {"input": 0.003, "output": 0.015}

        cost = calculate_cost(tokens, cost_per_1k)

        expected = (1000 / 1000) * 0.003 + (500 / 1000) * 0.015
        assert cost == pytest.approx(expected)

    def test_calculate_cost_zero_tokens(self):
        tokens = TokenUsage(input_tokens=0, output_tokens=0)
        cost = calculate_cost(tokens, {"input": 0.003, "output": 0.015})
        assert cost == 0.0

    def test_get_default_cost_claude(self):
        cost = get_default_cost("claude")
        assert cost["input"] == 0.003
        assert cost["output"] == 0.015

    def test_get_default_cost_unknown(self):
        cost = get_default_cost("unknown_agent")
        assert cost == {"input": 0, "output": 0}

    def test_format_cost_small(self):
        assert format_cost(0.0025) == "$0.0025"

    def test_format_cost_large(self):
        assert format_cost(1.50) == "$1.50"


class TestSessionTokens:
    def test_initial_state(self):
        session = SessionTokens(session_id="test", agent="claude")
        assert session.invocations == 0
        assert session.cumulative_total == 0
        assert session.context_remaining == 100000

    def test_add_invocation(self):
        session = SessionTokens(
            session_id="test", agent="claude", context_window_max=200000
        )
        tokens = TokenUsage(input_tokens=1000, output_tokens=500)

        record = session.add_invocation(tokens, cost=0.01, state="draft")

        assert session.invocations == 1
        assert session.cumulative_input == 1000
        assert session.cumulative_output == 500
        assert session.cumulative_total == 1500
        assert session.total_cost_usd == 0.01
        assert len(session.history) == 1

    def test_context_used_percent(self):
        session = SessionTokens(
            session_id="test", agent="claude", context_window_max=100000
        )
        session.cumulative_input = 50000
        session.cumulative_output = 10000

        assert session.context_used_percent == 60.0

    def test_context_remaining(self):
        session = SessionTokens(
            session_id="test", agent="claude", context_window_max=100000
        )
        session.cumulative_input = 80000
        session.cumulative_output = 15000

        assert session.context_remaining == 5000


class TestTokenTracker:
    def test_record_creates_session(self):
        tracker = TokenTracker("run-001")
        tokens = TokenUsage(input_tokens=100, output_tokens=50)

        record = tracker.record("claude", "draft", tokens, cost=0.005)

        assert "claude" in tracker.sessions
        assert record.agent == "claude"
        assert record.state == "draft"

    def test_record_updates_summary(self):
        tracker = TokenTracker("run-001")
        tokens1 = TokenUsage(input_tokens=100, output_tokens=50)
        tokens2 = TokenUsage(input_tokens=200, output_tokens=100)

        tracker.record("claude", "draft", tokens1, cost=0.005)
        tracker.record("gemini", "draft", tokens2, cost=0.003)

        summary = tracker.get_summary()
        assert summary.total_input_tokens == 300
        assert summary.total_output_tokens == 150
        assert summary.total_tokens == 450
        assert summary.total_cost_usd == pytest.approx(0.008)

    def test_by_state_tracking(self):
        tracker = TokenTracker("run-001")
        tokens = TokenUsage(input_tokens=100, output_tokens=50)

        tracker.record("claude", "draft", tokens, cost=0.005)
        tracker.record("claude", "draft", tokens, cost=0.005)
        tracker.record("claude", "audit", tokens, cost=0.005)

        summary = tracker.get_summary()
        assert summary.by_state["draft"] == 300
        assert summary.by_state["audit"] == 150

    def test_check_context_health_healthy(self):
        tracker = TokenTracker("run-001")
        tokens = TokenUsage(input_tokens=1000, output_tokens=500)
        tracker.record("claude", "draft", tokens, cost=0.005, context_window=200000)

        health = tracker.check_context_health("claude")

        assert health["status"] == "healthy"
        assert health["percent_used"] < 1

    def test_check_context_health_warning(self):
        tracker = TokenTracker("run-001")
        tokens = TokenUsage(input_tokens=85000, output_tokens=0)
        tracker.record("claude", "draft", tokens, cost=0.25, context_window=100000)

        health = tracker.check_context_health("claude")

        assert health["status"] == "warning"

    def test_check_context_health_critical(self):
        tracker = TokenTracker("run-001")
        tokens = TokenUsage(input_tokens=95000, output_tokens=0)
        tracker.record("claude", "draft", tokens, cost=0.28, context_window=100000)

        health = tracker.check_context_health("claude")

        assert health["status"] == "critical"

    def test_check_context_health_unknown_agent(self):
        tracker = TokenTracker("run-001")

        health = tracker.check_context_health("unknown")

        assert health["status"] == "unknown"


class TestEstimateRunCost:
    def test_estimate_basic(self):
        estimate = estimate_run_cost(
            states=["draft", "audit", "synthesize"],
            agents=["claude", "gemini"],
            tokens_per_state=1000,
        )

        assert "claude" in estimate["by_agent"]
        assert "gemini" in estimate["by_agent"]
        assert estimate["total_cost_usd"] > 0

    def test_estimate_formatted(self):
        estimate = estimate_run_cost(
            states=["draft"],
            agents=["claude"],
            tokens_per_state=100,
        )

        assert estimate["formatted"].startswith("$")
