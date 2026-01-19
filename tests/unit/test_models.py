"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from runner.models import (
    TokenUsage,
    AgentResult,
    AuditIssue,
    AuditResult,
    CircuitBreakerDecision,
    FanOutResult,
    StateResult,
)


class TestTokenUsage:
    def test_total_property(self):
        tokens = TokenUsage(input_tokens=100, output_tokens=50)
        assert tokens.total == 150

    def test_zero_tokens(self):
        tokens = TokenUsage(input_tokens=0, output_tokens=0)
        assert tokens.total == 0

    def test_negative_tokens_rejected(self):
        with pytest.raises(ValidationError):
            TokenUsage(input_tokens=-1, output_tokens=0)


class TestAgentResult:
    def test_successful_result(self):
        result = AgentResult(
            success=True,
            content="Hello world",
            tokens=TokenUsage(input_tokens=10, output_tokens=5),
        )
        assert result.success
        assert result.content == "Hello world"
        assert result.tokens.total == 15

    def test_failed_result_with_error(self):
        result = AgentResult(
            success=False,
            content="",
            tokens=TokenUsage(input_tokens=0, output_tokens=0),
            error="Connection timeout",
        )
        assert not result.success
        assert result.error == "Connection timeout"

    def test_optional_fields(self):
        result = AgentResult(
            success=True,
            content="test",
            tokens=TokenUsage(input_tokens=1, output_tokens=1),
        )
        assert result.session_id is None
        assert result.cost_usd is None
        assert result.duration_s == 0.0


class TestAuditResult:
    def test_valid_audit(self):
        audit = AuditResult(
            score=8,
            decision="proceed",
            feedback="Good draft with minor issues",
        )
        assert audit.score == 8
        assert audit.decision == "proceed"

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            AuditResult(score=0, decision="proceed", feedback="test")

        with pytest.raises(ValidationError):
            AuditResult(score=11, decision="proceed", feedback="test")

    def test_invalid_decision_rejected(self):
        with pytest.raises(ValidationError):
            AuditResult(score=5, decision="invalid", feedback="test")

    def test_has_critical_issues(self):
        audit = AuditResult(
            score=3,
            decision="halt",
            feedback="Critical problems",
            issues=[
                AuditIssue(severity="critical", issue="Missing hook", fix="Add sensory detail"),
                AuditIssue(severity="minor", issue="Typo", fix="Fix spelling"),
            ],
        )
        assert audit.has_critical_issues

    def test_no_critical_issues(self):
        audit = AuditResult(
            score=7,
            decision="proceed",
            feedback="Minor issues only",
            issues=[
                AuditIssue(severity="minor", issue="Could be tighter", fix="Remove filler"),
            ],
        )
        assert not audit.has_critical_issues


class TestCircuitBreakerDecision:
    def test_force_complete(self):
        decision = CircuitBreakerDecision(
            decision="force_complete",
            reasoning="Quality plateaued at 6/10",
            use_output="drafts/claude_draft.md",
        )
        assert decision.decision == "force_complete"
        assert decision.use_output == "drafts/claude_draft.md"

    def test_retry_different(self):
        decision = CircuitBreakerDecision(
            decision="retry_different",
            reasoning="Missing sensory details",
            retry_from="draft",
            retry_guidance="Focus on what you saw",
        )
        assert decision.decision == "retry_different"
        assert decision.retry_from == "draft"


class TestFanOutResult:
    def test_success_result(self):
        result = FanOutResult(
            agent="claude",
            status="success",
            output_path="drafts/claude_draft.md",
            tokens=TokenUsage(input_tokens=500, output_tokens=300),
            duration_s=12.5,
        )
        assert result.status == "success"
        assert result.tokens.total == 800

    def test_timeout_result(self):
        result = FanOutResult(
            agent="gemini",
            status="timeout",
            duration_s=300.0,
            error="Agent timed out",
        )
        assert result.status == "timeout"
        assert result.output_path is None


class TestStateResult:
    def test_state_with_outputs(self):
        result = StateResult(
            state_name="draft",
            transition="all_success",
            outputs={
                "claude": FanOutResult(agent="claude", status="success"),
                "gemini": FanOutResult(agent="gemini", status="success"),
            },
            duration_s=25.0,
            total_cost_usd=0.05,
        )
        assert len(result.outputs) == 2
        assert result.transition == "all_success"
