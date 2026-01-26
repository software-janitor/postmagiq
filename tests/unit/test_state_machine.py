"""Tests for state machine."""

import pytest
import os
from unittest.mock import patch, MagicMock

from runner.state_machine import StateMachine
from runner.models import TokenUsage, AgentResult
from tests.conftest import MockAgent, FailingAgent


@pytest.fixture
def mock_agents():
    return {
        "claude": MockAgent(["Draft from Claude"]),
        "gemini": MockAgent(["Draft from Gemini"]),
        "codex": MockAgent(["Draft from Codex"]),
    }


@pytest.fixture
def basic_config(tmp_path):
    return {
        "states": {
            "start": {"type": "initial", "next": "draft"},
            "draft": {
                "type": "fan-out",
                "agents": ["claude", "gemini"],
                "output": str(tmp_path / "drafts/{agent}_draft.md"),
                "transitions": {
                    "all_success": "complete",
                    "partial_success": "complete",
                    "all_failure": "halt",
                },
            },
            "complete": {"type": "terminal"},
            "halt": {"type": "terminal", "error": True},
        },
        "settings": {
            "timeout_per_agent": 30,
            "parallel_fanout": False,
        },
    }


class TestStateMachine:
    def test_run_basic_workflow(self, basic_config, mock_agents, tmp_path):
        sm = StateMachine(basic_config, agents=mock_agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"
        assert (tmp_path / "drafts/claude_draft.md").exists()
        assert (tmp_path / "drafts/gemini_draft.md").exists()

    def test_fanout_creates_files(self, basic_config, mock_agents, tmp_path):
        sm = StateMachine(basic_config, agents=mock_agents)
        sm.initialize("test-run")

        sm.run()

        claude_content = (tmp_path / "drafts/claude_draft.md").read_text()
        assert "Draft from Claude" in claude_content

    def test_partial_failure_continues(self, basic_config, tmp_path):
        agents = {
            "claude": MockAgent(["Success"]),
            "gemini": FailingAgent([], fail_after=0),
        }

        sm = StateMachine(basic_config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"
        assert (tmp_path / "drafts/claude_draft.md").exists()
        assert not (tmp_path / "drafts/gemini_draft.md").exists()

    def test_all_failure_halts(self, basic_config, tmp_path):
        agents = {
            "claude": FailingAgent([], fail_after=0),
            "gemini": FailingAgent([], fail_after=0),
        }

        sm = StateMachine(basic_config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "halt"

    def test_circuit_breaker_triggers(self, tmp_path):
        config = {
            "states": {
                "start": {"type": "initial", "next": "loop"},
                "loop": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "transitions": {"success": "loop"},
                },
                "halt": {"type": "terminal"},
            },
            "circuit_breaker": {
                "rules": [{"name": "state_visit_limit", "limit": 3}]
            },
            "settings": {"timeout_per_agent": 30},
        }
        agents = {"claude": MockAgent(["ok"])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result.get("circuit_break") is True
        assert result["rule"] == "state_visit_limit"

    def test_unknown_state_halts(self, tmp_path):
        config = {
            "states": {
                "start": {"type": "initial", "next": "nonexistent"},
            }
        }

        sm = StateMachine(config)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "halt"
        assert "Unknown state" in result.get("error", "")

    def test_log_callback_called(self, basic_config, mock_agents):
        logs = []
        sm = StateMachine(
            basic_config, agents=mock_agents, log_callback=lambda x: logs.append(x)
        )
        sm.initialize("test-run")

        sm.run()

        events = [log.get("event") for log in logs]
        assert "state_enter" in events
        assert "state_complete" in events
        assert "transition" in events


class TestStateMachineRetry:
    def test_retry_feedback_stored(self, tmp_path):
        config = {
            "states": {
                "start": {"type": "initial", "next": "check"},
                "check": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "transitions": {
                        "proceed": "complete",
                        "retry": "draft",
                        "halt": "halt",
                    },
                },
                "draft": {
                    "type": "single",
                    "agent": "writer",
                    "output": str(tmp_path / "draft.md"),
                    "transitions": {"success": "check"},
                },
                "complete": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        audit_response = '{"score": 4, "decision": "retry", "feedback": "Add more detail"}'
        agents = {
            "auditor": MockAgent([audit_response, '{"score": 8, "decision": "proceed", "feedback": "Good"}']),
            "writer": MockAgent(["Draft v1", "Draft v2"]),
        }

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"


class TestStateMachineInputFiles:
    def test_resolve_single_file(self, tmp_path):
        test_file = tmp_path / "input.md"
        test_file.write_text("content")

        config = {"states": {}}
        sm = StateMachine(config)

        files = sm._resolve_input_files(str(test_file))

        assert len(files) == 1
        assert files[0] == str(test_file)

    def test_resolve_glob_pattern(self, tmp_path):
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")

        config = {"states": {}}
        sm = StateMachine(config)

        files = sm._resolve_input_files(str(tmp_path / "*.md"))

        assert len(files) == 2

    def test_resolve_nonexistent_file(self, tmp_path):
        config = {"states": {}}
        sm = StateMachine(config)

        files = sm._resolve_input_files(str(tmp_path / "missing.md"))

        assert len(files) == 0


class TestStateMachinePromptBuilding:
    def test_build_prompt_with_context(self, tmp_path):
        config = {"states": {}}
        sm = StateMachine(config)

        prompt = sm._build_prompt("Persona text", [], context="Extra context")

        assert "Persona text" in prompt
        assert "Extra context" in prompt

    def test_build_prompt_with_files(self, tmp_path):
        test_file = tmp_path / "input.md"
        test_file.write_text("File content here")

        config = {"states": {}}
        sm = StateMachine(config)

        prompt = sm._build_prompt("Persona", [str(test_file)])

        assert "File content here" in prompt
        assert str(test_file) in prompt


class TestStateMachineAuditFeedback:
    def test_audit_feedback_from_files(self, tmp_path):
        """Test that audit feedback is read from files when database is not available."""
        # Create audit files
        audits_dir = tmp_path / "audits"
        audits_dir.mkdir()
        (audits_dir / "claude_audit.json").write_text('{"score": 8, "feedback": "Good structure"}')
        (audits_dir / "gemini_audit.json").write_text('{"score": 7, "feedback": "Needs more detail"}')

        config = {"states": {}}
        sm = StateMachine(config, run_dir=str(tmp_path))
        sm.initialize("test-run")

        feedback = sm._get_audit_feedback_for_writers()

        assert feedback is not None
        assert "Previous Auditor Feedback" in feedback
        assert "Claude" in feedback
        assert "Gemini" in feedback
        assert "Good structure" in feedback
        assert "Needs more detail" in feedback

    def test_audit_feedback_included_in_draft_prompt(self, tmp_path, mock_agents):
        """Test that audit feedback is included when executing draft state."""
        # Create audit files
        audits_dir = tmp_path / "audits"
        audits_dir.mkdir()
        (audits_dir / "claude_audit.json").write_text('{"score": 8, "feedback": "Improve opening"}')

        config = {
            "states": {
                "start": {"type": "initial", "next": "draft"},
                "draft": {
                    "type": "fan-out",
                    "agents": ["claude"],
                    "output": str(tmp_path / "drafts/{agent}_draft.md"),
                    "transitions": {"all_success": "complete"},
                },
                "complete": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30, "parallel_fanout": False},
        }

        # Track the prompt that was passed to the agent
        captured_prompt = []
        original_invoke = mock_agents["claude"].invoke

        def capturing_invoke(prompt):
            captured_prompt.append(prompt)
            return original_invoke(prompt)

        mock_agents["claude"].invoke = capturing_invoke

        sm = StateMachine(config, agents=mock_agents, run_dir=str(tmp_path))
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"
        assert len(captured_prompt) == 1
        assert "Previous Auditor Feedback" in captured_prompt[0]
        assert "Improve opening" in captured_prompt[0]

    def test_no_feedback_without_audit_files(self, tmp_path):
        """Test that no feedback is returned when no audit files exist."""
        config = {"states": {}}
        sm = StateMachine(config, run_dir=str(tmp_path))
        sm.initialize("test-run")

        feedback = sm._get_audit_feedback_for_writers()

        assert feedback is None

    def test_final_audit_feedback_from_files(self, tmp_path):
        """Test that final audit feedback is read from files."""
        # Create final audit files
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        (final_dir / "claude_final_audit.json").write_text('{"score": 9, "feedback": "Almost perfect"}')
        (final_dir / "gemini_final_audit.json").write_text('{"score": 8, "feedback": "Good but needs polish"}')

        config = {"states": {}}
        sm = StateMachine(config, run_dir=str(tmp_path))
        sm.initialize("test-run")

        feedback = sm._get_final_audit_feedback_for_synthesizer()

        assert feedback is not None
        assert "Previous Final Audit Feedback" in feedback
        assert "Claude" in feedback
        assert "Gemini" in feedback
        assert "Almost perfect" in feedback
        assert "Good but needs polish" in feedback

    def test_final_audit_feedback_included_in_synthesize_prompt(self, tmp_path, mock_agents):
        """Test that final audit feedback is included when executing synthesize state."""
        # Create final audit files
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        (final_dir / "claude_final_audit.json").write_text('{"score": 7, "feedback": "Fix the opening"}')

        config = {
            "states": {
                "start": {"type": "initial", "next": "synthesize"},
                "synthesize": {
                    "type": "orchestrator-task",
                    "agent": "claude",
                    "output": str(tmp_path / "final/final_post.md"),
                    "transitions": {"success": "complete"},
                },
                "complete": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # Track the prompt that was passed to the agent
        captured_prompt = []

        def capturing_invoke_with_session(session_id, prompt):
            captured_prompt.append(prompt)
            return mock_agents["claude"].invoke(prompt)

        mock_agents["claude"].invoke_with_session = capturing_invoke_with_session

        sm = StateMachine(config, agents=mock_agents, run_dir=str(tmp_path))
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"
        assert len(captured_prompt) == 1
        assert "Previous Final Audit Feedback" in captured_prompt[0]
        assert "Fix the opening" in captured_prompt[0]


class TestStateMachineTransitionResolution:
    """Tests for transition resolution from state results."""

    def test_single_non_audit_success_transition(self, tmp_path):
        """Single state with non-audit output uses success/failure transitions."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "review"},
                "review": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "review.json"),
                    "output_type": "review",
                    "transitions": {
                        "success": "process",
                        "retry": "feedback",
                        "failure": "halt",
                    },
                },
                "process": {"type": "terminal"},
                "feedback": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # Non-audit response (plain text, not JSON)
        agents = {"claude": MockAgent(["Story looks good, proceed to process"])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should use 'success' transition since output is not AuditResult
        assert result["final_state"] == "process"

    def test_single_non_audit_failure_transition(self, tmp_path):
        """Single state with failed agent uses failure transition."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "review"},
                "review": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "review.json"),
                    "output_type": "review",
                    "transitions": {
                        "success": "process",
                        "failure": "halt",
                    },
                },
                "process": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        agents = {"claude": FailingAgent([], fail_after=0)}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should use 'failure' transition
        assert result["final_state"] == "halt"

    def test_single_audit_proceed_transition(self, tmp_path):
        """Single state with audit output uses proceed/retry/halt transitions."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "audit"},
                "audit": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "output_type": "audit",
                    "transitions": {
                        "proceed": "complete",
                        "retry": "revise",
                        "halt": "error",
                    },
                },
                "complete": {"type": "terminal"},
                "revise": {"type": "terminal"},
                "error": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # Valid AuditResult JSON with proceed decision
        audit_response = '{"score": 9, "decision": "proceed", "feedback": "Excellent work"}'
        agents = {"auditor": MockAgent([audit_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"

    def test_single_audit_retry_transition(self, tmp_path):
        """Audit with retry decision transitions to retry target."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "audit"},
                "audit": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "output_type": "audit",
                    "transitions": {
                        "proceed": "complete",
                        "retry": "revise",
                        "halt": "error",
                    },
                },
                "complete": {"type": "terminal"},
                "revise": {"type": "terminal"},
                "error": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # AuditResult with retry decision
        audit_response = '{"score": 4, "decision": "retry", "feedback": "Needs improvement"}'
        agents = {"auditor": MockAgent([audit_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "revise"

    def test_single_audit_halt_transition(self, tmp_path):
        """Audit with halt decision transitions to halt target."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "audit"},
                "audit": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "output_type": "audit",
                    "transitions": {
                        "proceed": "complete",
                        "retry": "revise",
                        "halt": "error",
                    },
                },
                "complete": {"type": "terminal"},
                "revise": {"type": "terminal"},
                "error": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # AuditResult with halt decision
        audit_response = '{"score": 1, "decision": "halt", "feedback": "Critical issues"}'
        agents = {"auditor": MockAgent([audit_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "error"

    def test_invalid_transition_halts_workflow(self, tmp_path):
        """Invalid transition name causes workflow to halt with error."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "review"},
                "review": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "review.json"),
                    "transitions": {
                        # Missing 'success' - only has 'proceed'
                        "proceed": "process",
                        "failure": "halt",
                    },
                },
                "process": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # Non-audit response returns 'success' but config only has 'proceed'
        agents = {"claude": MockAgent(["Success response"])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "halt"
        assert "No valid transition" in result.get("error", "")

    def test_audit_in_markdown_fence_parsed(self, tmp_path):
        """Audit result wrapped in markdown JSON fence is parsed correctly."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "audit"},
                "audit": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "output_type": "audit",
                    "transitions": {
                        "proceed": "complete",
                        "retry": "revise",
                        "halt": "error",
                    },
                },
                "complete": {"type": "terminal"},
                "revise": {"type": "terminal"},
                "error": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # AuditResult wrapped in markdown fence (common LLM output format)
        audit_response = '''Here is my assessment:

```json
{"score": 8, "decision": "proceed", "feedback": "Good work"}
```

The post is ready.'''
        agents = {"auditor": MockAgent([audit_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"

    def test_malformed_audit_falls_back_to_success(self, tmp_path):
        """Malformed audit JSON falls back to success/failure transitions."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "audit"},
                "audit": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "output_type": "audit",
                    "transitions": {
                        "proceed": "complete",
                        "retry": "revise",
                        "halt": "error",
                        "success": "fallback",  # Fallback for malformed audit
                    },
                },
                "complete": {"type": "terminal"},
                "revise": {"type": "terminal"},
                "error": {"type": "terminal"},
                "fallback": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # Invalid JSON that can't be parsed as AuditResult
        agents = {"auditor": MockAgent(["This is not valid JSON"])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should fall back to 'success' transition
        assert result["final_state"] == "fallback"
