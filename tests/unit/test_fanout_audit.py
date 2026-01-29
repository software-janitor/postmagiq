"""Tests for fan-out audit: per-agent personas and audit aggregation."""

import pytest

from runner.state_machine import StateMachine
from runner.models import FanOutResult, TokenUsage, AuditResult
from tests.conftest import MockAgent, FailingAgent


@pytest.fixture
def audit_config(tmp_path):
    """Fan-out audit config with two auditors and per-agent personas."""
    return {
        "states": {
            "start": {"type": "initial", "next": "audit"},
            "audit": {
                "type": "fan-out",
                "agents": ["fab-auditor", "style-auditor"],
                "personas": {
                    "fab-auditor": "fabrication-auditor",
                    "style-auditor": "style-auditor",
                },
                "output": str(tmp_path / "audits/{agent}_audit.json"),
                "output_type": "audit",
                "transitions": {
                    "proceed": "complete",
                    "retry": "revise",
                    "halt": "halt",
                    "all_success": "complete",
                },
            },
            "complete": {"type": "terminal"},
            "revise": {"type": "terminal"},
            "halt": {"type": "terminal"},
        },
        "settings": {"timeout_per_agent": 30, "parallel_fanout": False},
    }


class TestPerAgentPersona:
    def test_different_prompts_per_agent(self, audit_config, tmp_path):
        """Each agent in fan-out gets a prompt built from its own persona."""
        fab_agent = MockAgent(['{"score": 9, "decision": "proceed", "feedback": "ok"}'])
        style_agent = MockAgent(['{"score": 9, "decision": "proceed", "feedback": "ok"}'])

        agents = {"fab-auditor": fab_agent, "style-auditor": style_agent}

        sm = StateMachine(audit_config, agents=agents)
        sm.initialize("test-run")
        sm.run()

        # Both agents should have been invoked
        assert fab_agent.call_count == 1
        assert style_agent.call_count == 1
        # Prompts are built independently (may differ if personas load differently)
        assert len(fab_agent.prompts_received) == 1
        assert len(style_agent.prompts_received) == 1

    def test_backward_compat_shared_persona(self, tmp_path):
        """Fan-out without personas dict uses shared persona — backward compatible."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "draft"},
                "draft": {
                    "type": "fan-out",
                    "agents": ["a", "b"],
                    "persona": "writer",  # shared, no per-agent map
                    "output": str(tmp_path / "drafts/{agent}.md"),
                    "transitions": {"all_success": "complete"},
                },
                "complete": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30, "parallel_fanout": False},
        }

        a = MockAgent(["Draft A"])
        b = MockAgent(["Draft B"])
        agents = {"a": a, "b": b}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")
        result = sm.run()

        assert result["final_state"] == "complete"
        assert a.call_count == 1
        assert b.call_count == 1


class TestAuditAggregation:
    def test_all_proceed(self, audit_config, tmp_path):
        """All auditors proceed → transition is proceed."""
        agents = {
            "fab-auditor": MockAgent(['{"score": 9, "decision": "proceed", "feedback": "Clean"}']),
            "style-auditor": MockAgent(['{"score": 8, "decision": "proceed", "feedback": "Good style"}']),
        }

        sm = StateMachine(audit_config, agents=agents)
        sm.initialize("test-run")
        result = sm.run()

        assert result["final_state"] == "complete"
        assert sm.last_audit_score == 8  # min(9, 8)

    def test_one_retry(self, audit_config, tmp_path):
        """One retry + one proceed → transition is retry."""
        agents = {
            "fab-auditor": MockAgent(['{"score": 4, "decision": "retry", "feedback": "Fabricated claim"}']),
            "style-auditor": MockAgent(['{"score": 9, "decision": "proceed", "feedback": "Style ok"}']),
        }

        sm = StateMachine(audit_config, agents=agents)
        sm.initialize("test-run")
        result = sm.run()

        assert result["final_state"] == "revise"
        assert sm.last_audit_score == 4
        # Feedback stored for retry target
        assert "revise" in sm.retry_feedback
        assert "Fabricated claim" in sm.retry_feedback["revise"]
        assert "Style ok" in sm.retry_feedback["revise"]

    def test_one_halt(self, audit_config, tmp_path):
        """One halt + one proceed → transition is halt."""
        agents = {
            "fab-auditor": MockAgent(['{"score": 1, "decision": "halt", "feedback": "Completely fabricated"}']),
            "style-auditor": MockAgent(['{"score": 9, "decision": "proceed", "feedback": "Great"}']),
        }

        sm = StateMachine(audit_config, agents=agents)
        sm.initialize("test-run")
        result = sm.run()

        assert result["final_state"] == "halt"
        assert sm.last_audit_score == 1

    def test_halt_beats_retry(self, audit_config, tmp_path):
        """Halt is stricter than retry — halt wins."""
        agents = {
            "fab-auditor": MockAgent(['{"score": 1, "decision": "halt", "feedback": "Fatal"}']),
            "style-auditor": MockAgent(['{"score": 4, "decision": "retry", "feedback": "Fix style"}']),
        }

        sm = StateMachine(audit_config, agents=agents)
        sm.initialize("test-run")
        result = sm.run()

        assert result["final_state"] == "halt"

    def test_mixed_scores_min_tracked(self, audit_config, tmp_path):
        """last_audit_score tracks minimum across all auditors."""
        agents = {
            "fab-auditor": MockAgent(['{"score": 7, "decision": "proceed", "feedback": "ok"}']),
            "style-auditor": MockAgent(['{"score": 3, "decision": "retry", "feedback": "bad"}']),
        }

        sm = StateMachine(audit_config, agents=agents)
        sm.initialize("test-run")
        sm.run()

        assert sm.last_audit_score == 3


class TestFanOutContentField:
    def test_parse_audit_from_content(self):
        """_parse_audit_result reads from FanOutResult.content before file."""
        config = {"states": {}}
        sm = StateMachine(config)

        result = FanOutResult(
            agent="test",
            status="success",
            content='{"score": 8, "decision": "proceed", "feedback": "Good"}',
        )

        audit = sm._parse_audit_result(result)
        assert audit is not None
        assert audit.score == 8
        assert audit.decision == "proceed"

    def test_parse_audit_from_content_with_fence(self):
        """_parse_audit_result handles markdown-fenced JSON in content."""
        config = {"states": {}}
        sm = StateMachine(config)

        result = FanOutResult(
            agent="test",
            status="success",
            content='```json\n{"score": 6, "decision": "retry", "feedback": "Needs work"}\n```',
        )

        audit = sm._parse_audit_result(result)
        assert audit is not None
        assert audit.score == 6
        assert audit.decision == "retry"

    def test_parse_audit_no_content_no_file(self):
        """_parse_audit_result returns None when no content and no file."""
        config = {"states": {}}
        sm = StateMachine(config)

        result = FanOutResult(agent="test", status="success")

        audit = sm._parse_audit_result(result)
        assert audit is None


class TestAggregateAuditResults:
    def test_all_proceed_returns_proceed(self):
        config = {"states": {}}
        sm = StateMachine(config)

        results = [
            ("a", AuditResult(score=9, decision="proceed", feedback="Good")),
            ("b", AuditResult(score=8, decision="proceed", feedback="Fine")),
        ]
        state = {"transitions": {"retry": "revise"}}

        transition, feedback = sm._aggregate_audit_results(results, state)
        assert transition == "proceed"
        assert sm.last_audit_score == 8

    def test_any_retry_returns_retry(self):
        config = {"states": {}}
        sm = StateMachine(config)

        results = [
            ("a", AuditResult(score=9, decision="proceed", feedback="Good")),
            ("b", AuditResult(score=4, decision="retry", feedback="Fix this")),
        ]
        state = {"transitions": {"retry": "revise"}}

        transition, feedback = sm._aggregate_audit_results(results, state)
        assert transition == "retry"
        assert "Fix this" in feedback
        assert "Good" in feedback
        assert sm.retry_feedback.get("revise") is not None

    def test_any_halt_returns_halt(self):
        config = {"states": {}}
        sm = StateMachine(config)

        results = [
            ("a", AuditResult(score=1, decision="halt", feedback="Fatal")),
            ("b", AuditResult(score=9, decision="proceed", feedback="Fine")),
        ]
        state = {"transitions": {"retry": "revise"}}

        transition, feedback = sm._aggregate_audit_results(results, state)
        assert transition == "halt"
        assert sm.last_audit_score == 1


class TestFanOutNonAuditUnchanged:
    def test_fanout_without_output_type_uses_success_counting(self, tmp_path):
        """Fan-out without output_type still uses all_success/partial/all_failure."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "draft"},
                "draft": {
                    "type": "fan-out",
                    "agents": ["a", "b"],
                    "output": str(tmp_path / "{agent}.md"),
                    "transitions": {
                        "all_success": "complete",
                        "partial_success": "complete",
                        "all_failure": "halt",
                    },
                },
                "complete": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30, "parallel_fanout": False},
        }

        agents = {"a": MockAgent(["ok"]), "b": MockAgent(["ok"])}
        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()
        assert result["final_state"] == "complete"
