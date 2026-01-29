"""Tests for state machine."""

import pytest
import os
import threading
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
                    "output_type": "audit",  # Required for audit parsing
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


class TestDefaultTransitions:
    """Tests for default transitions merging with state-specific transitions."""

    def test_default_transitions_used_when_state_has_none(self, tmp_path):
        """State with no transitions uses default transitions."""
        config = {
            "default_transitions": {
                "success": "complete",
                "failure": "halt",
            },
            "states": {
                "start": {"type": "initial", "next": "process"},
                "process": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "output_type": "processed",
                    # No transitions defined - should use defaults
                },
                "complete": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        agents = {"claude": MockAgent(["Success output"])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should use default 'success' -> 'complete'
        assert result["final_state"] == "complete"

    def test_state_transitions_override_defaults(self, tmp_path):
        """State-specific transitions override default transitions."""
        config = {
            "default_transitions": {
                "success": "complete",
                "failure": "halt",
            },
            "states": {
                "start": {"type": "initial", "next": "process"},
                "process": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "output_type": "processed",
                    "transitions": {
                        "success": "custom_next",  # Override default
                    },
                },
                "custom_next": {"type": "terminal"},
                "complete": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        agents = {"claude": MockAgent(["Success output"])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should use state-specific 'success' -> 'custom_next'
        assert result["final_state"] == "custom_next"

    def test_default_and_state_transitions_merge(self, tmp_path):
        """State transitions merge with defaults - state overrides, defaults fill gaps."""
        config = {
            "default_transitions": {
                "success": "complete",
                "failure": "halt",
                "retry": "draft",
            },
            "states": {
                "start": {"type": "initial", "next": "audit"},
                "audit": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "output_type": "audit",
                    "transitions": {
                        "proceed": "approved",  # State-specific
                        # 'retry' will come from defaults -> 'draft'
                    },
                },
                "approved": {"type": "terminal"},
                "draft": {"type": "terminal"},
                "complete": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # Audit returning retry should use default retry transition
        audit_response = '{"score": 4, "decision": "retry", "feedback": "Needs work"}'
        agents = {"auditor": MockAgent([audit_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should use default 'retry' -> 'draft'
        assert result["final_state"] == "draft"

    def test_default_failure_transition(self, tmp_path):
        """Default failure transition used when agent fails."""
        config = {
            "default_transitions": {
                "success": "complete",
                "failure": "error_state",
            },
            "states": {
                "start": {"type": "initial", "next": "process"},
                "process": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "output_type": "processed",
                    # No transitions - use defaults
                },
                "complete": {"type": "terminal"},
                "error_state": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        agents = {"claude": FailingAgent([], fail_after=0)}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should use default 'failure' -> 'error_state'
        assert result["final_state"] == "error_state"

    def test_get_transitions_method(self, tmp_path):
        """Test _get_transitions method directly."""
        config = {
            "default_transitions": {
                "success": "default_success",
                "failure": "default_failure",
                "retry": "default_retry",
            },
            "states": {},
        }

        sm = StateMachine(config)

        # State with no transitions
        state_config = {}
        transitions = sm._get_transitions(state_config)
        assert transitions["success"] == "default_success"
        assert transitions["failure"] == "default_failure"
        assert transitions["retry"] == "default_retry"

        # State with partial overrides
        state_config = {"transitions": {"success": "custom_success"}}
        transitions = sm._get_transitions(state_config)
        assert transitions["success"] == "custom_success"  # Overridden
        assert transitions["failure"] == "default_failure"  # From defaults
        assert transitions["retry"] == "default_retry"  # From defaults

        # State with full overrides
        state_config = {
            "transitions": {
                "success": "s1",
                "failure": "f1",
                "retry": "r1",
            }
        }
        transitions = sm._get_transitions(state_config)
        assert transitions["success"] == "s1"
        assert transitions["failure"] == "f1"
        assert transitions["retry"] == "r1"


class TestNonAuditJsonOutput:
    """Tests for JSON outputs that should NOT be parsed as audit results."""

    def test_processed_json_not_parsed_as_audit(self, tmp_path):
        """JSON output with output_type='processed' should not be parsed as audit."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "process"},
                "process": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "processed.json"),
                    "output_type": "processed",  # Not audit!
                    "transitions": {
                        "success": "complete",
                        "retry": "feedback",  # Should NOT be triggered
                        "failure": "halt",
                    },
                },
                "complete": {"type": "terminal"},
                "feedback": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # JSON output that looks like it could be parsed but isn't an audit
        json_response = '''{
            "title": "My Story",
            "hook": "Something interesting",
            "story": "The full story here",
            "shape": "PARTIAL"
        }'''
        agents = {"claude": MockAgent([json_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should use 'success' transition, NOT try to parse as audit
        assert result["final_state"] == "complete"

    def test_draft_json_not_parsed_as_audit(self, tmp_path):
        """JSON output with output_type='draft' should not be parsed as audit."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "draft"},
                "draft": {
                    "type": "single",
                    "agent": "writer",
                    "output": str(tmp_path / "draft.json"),
                    "output_type": "draft",
                    "transitions": {
                        "success": "complete",
                        "retry": "revise",
                        "failure": "halt",
                    },
                },
                "complete": {"type": "terminal"},
                "revise": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # Some JSON in the output
        json_response = '{"content": "Draft content here", "version": 1}'
        agents = {"writer": MockAgent([json_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"

    def test_review_output_type_parsed_as_audit(self, tmp_path):
        """JSON output with output_type='review' SHOULD be parsed as audit."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "review"},
                "review": {
                    "type": "single",
                    "agent": "reviewer",
                    "output": str(tmp_path / "review.json"),
                    "output_type": "review",  # Should be parsed as audit
                    "transitions": {
                        "proceed": "complete",
                        "retry": "feedback",
                        "success": "complete",
                    },
                },
                "complete": {"type": "terminal"},
                "feedback": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # Valid audit result
        audit_response = '{"score": 9, "decision": "proceed", "feedback": "Good"}'
        agents = {"reviewer": MockAgent([audit_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        # Should parse as audit and use 'proceed' transition
        assert result["final_state"] == "complete"

    def test_final_audit_output_type_parsed(self, tmp_path):
        """JSON output with output_type='final_audit' SHOULD be parsed as audit."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "final_check"},
                "final_check": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "final_audit.json"),
                    "output_type": "final_audit",
                    "transitions": {
                        "proceed": "done",
                        "retry": "revise",
                    },
                },
                "done": {"type": "terminal"},
                "revise": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        audit_response = '{"score": 8, "decision": "proceed", "feedback": "Approved"}'
        agents = {"auditor": MockAgent([audit_response])}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "done"


class TestFullWorkflowTransitions:
    """End-to-end tests simulating full workflow with all transition types."""

    def test_happy_path_workflow(self, tmp_path):
        """Test complete workflow: review -> process -> draft -> audit -> approve."""
        config = {
            "default_transitions": {
                "success": "complete",
                "failure": "halt",
                "proceed": "human-approval",
                "halt": "halt",
            },
            "states": {
                "start": {"type": "initial", "next": "review"},
                "review": {
                    "type": "single",
                    "agent": "reviewer",
                    "output": str(tmp_path / "review.json"),
                    "output_type": "review",
                    "transitions": {
                        "proceed": "process",
                        "success": "process",
                    },
                },
                "process": {
                    "type": "single",
                    "agent": "processor",
                    "output": str(tmp_path / "processed.json"),
                    "output_type": "processed",
                    "transitions": {"success": "draft"},
                },
                "draft": {
                    "type": "single",
                    "agent": "writer",
                    "output": str(tmp_path / "draft.md"),
                    "output_type": "draft",
                    "transitions": {"success": "audit"},
                },
                "audit": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "output_type": "audit",
                    "transitions": {"proceed": "complete"},
                },
                "complete": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        agents = {
            "reviewer": MockAgent(['{"score": 9, "decision": "proceed", "feedback": "Good story"}']),
            "processor": MockAgent(['{"title": "Test", "story": "Content"}']),
            "writer": MockAgent(["# Draft Post\n\nContent here"]),
            "auditor": MockAgent(['{"score": 9, "decision": "proceed", "feedback": "Approved"}']),
        }

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"
        assert (tmp_path / "review.json").exists()
        assert (tmp_path / "processed.json").exists()
        assert (tmp_path / "draft.md").exists()
        assert (tmp_path / "audit.json").exists()

    def test_retry_loop_workflow(self, tmp_path):
        """Test workflow with retry: audit fails, revise, audit passes."""
        config = {
            "default_transitions": {
                "success": "complete",
                "failure": "halt",
            },
            "states": {
                "start": {"type": "initial", "next": "draft"},
                "draft": {
                    "type": "single",
                    "agent": "writer",
                    "output": str(tmp_path / "draft.md"),
                    "output_type": "draft",
                    "transitions": {"success": "audit"},
                },
                "audit": {
                    "type": "single",
                    "agent": "auditor",
                    "output": str(tmp_path / "audit.json"),
                    "output_type": "audit",
                    "transitions": {
                        "proceed": "complete",
                        "retry": "revise",
                    },
                },
                "revise": {
                    "type": "single",
                    "agent": "writer",
                    "output": str(tmp_path / "revised.md"),
                    "output_type": "draft",
                    "transitions": {"success": "audit"},
                },
                "complete": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        agents = {
            "writer": MockAgent(["Draft v1", "Draft v2 (revised)"]),
            "auditor": MockAgent([
                '{"score": 4, "decision": "retry", "feedback": "Needs improvement"}',
                '{"score": 9, "decision": "proceed", "feedback": "Much better"}',
            ]),
        }

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "complete"
        # Writer called twice (draft + revise)
        assert agents["writer"].call_count == 2
        # Auditor called twice
        assert agents["auditor"].call_count == 2

    def test_halt_workflow(self, tmp_path):
        """Test workflow that halts on critical audit failure."""
        config = {
            "default_transitions": {
                "success": "complete",
                "failure": "halt",
                "halt": "halt",
            },
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
                    },
                },
                "revise": {"type": "terminal"},
                "complete": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        agents = {
            "auditor": MockAgent(['{"score": 1, "decision": "halt", "feedback": "Critical failure"}']),
        }

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "halt"

    def test_agent_failure_uses_failure_transition(self, tmp_path):
        """Test that agent failure uses failure transition."""
        config = {
            "default_transitions": {
                "success": "next",
                "failure": "error_handler",
            },
            "states": {
                "start": {"type": "initial", "next": "process"},
                "process": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "output_type": "processed",
                },
                "next": {"type": "terminal"},
                "error_handler": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        agents = {"claude": FailingAgent([], fail_after=0)}

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")

        result = sm.run()

        assert result["final_state"] == "error_handler"


class TestWaitForApproval:
    """Tests for _wait_for_approval() method."""

    def test_returns_decision_and_feedback(self):
        """_wait_for_approval returns decision/feedback when event is set."""
        config = {"states": {}}
        sm = StateMachine(config)
        sm.initialize("test-run")

        def submit_after_delay():
            import time
            # Wait for awaiting_approval to be set by _wait_for_approval
            for _ in range(100):
                if sm.awaiting_approval:
                    sm.submit_approval("approved", "looks good")
                    return
                time.sleep(0.05)

        t = threading.Thread(target=submit_after_delay)
        t.start()

        decision, feedback = sm._wait_for_approval(timeout=5)
        t.join()

        assert decision == "approved"
        assert feedback == "looks good"

    def test_returns_abort_on_timeout(self):
        """_wait_for_approval returns ('abort', None) when timeout expires."""
        config = {"states": {}}
        sm = StateMachine(config)
        sm.initialize("test-run")

        decision, feedback = sm._wait_for_approval(timeout=0.1)

        assert decision == "abort"
        assert feedback is None

    def test_resets_awaiting_approval_after_response(self):
        """awaiting_approval is False after _wait_for_approval returns."""
        config = {"states": {}}
        sm = StateMachine(config)
        sm.initialize("test-run")

        def submit_after_delay():
            import time
            for _ in range(100):
                if sm.awaiting_approval:
                    sm.submit_approval("abort")
                    return
                time.sleep(0.05)

        t = threading.Thread(target=submit_after_delay)
        t.start()

        sm._wait_for_approval(timeout=5)
        t.join()

        assert sm.awaiting_approval is False

    def test_resets_awaiting_approval_after_timeout(self):
        """awaiting_approval is False after timeout."""
        config = {"states": {}}
        sm = StateMachine(config)
        sm.initialize("test-run")

        sm._wait_for_approval(timeout=0.1)

        assert sm.awaiting_approval is False


class TestCircuitBreakerApproval:
    """Tests for circuit breaker approval flow."""

    def test_circuit_break_skip_proceeds(self, tmp_path):
        """Circuit breaker with approval_callback skips forward on 'approved'."""
        # Use "next" for looping and "proceed" as the skip target.
        # The circuit breaker skip logic looks for transitions.get("success")
        # then transitions.get("proceed"). Since "success" isn't in transitions
        # here, it falls through to "proceed" -> "done".
        config = {
            "states": {
                "start": {"type": "initial", "next": "loop"},
                "loop": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "next": "loop",
                    "transitions": {
                        "proceed": "done",
                    },
                },
                "done": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "circuit_breaker": {
                "rules": [{"name": "state_visit_limit", "limit": 3}]
            },
            "settings": {"timeout_per_agent": 30},
        }
        agents = {"claude": MockAgent(["ok"])}

        approval_calls = []

        def approval_callback(data):
            approval_calls.append(data)

        sm = StateMachine(
            config,
            agents=agents,
            approval_callback=approval_callback,
        )
        sm.initialize("test-run")

        def submit_skip():
            import time
            for _ in range(100):
                if sm.awaiting_approval:
                    sm.submit_approval("approved")
                    return
                time.sleep(0.05)

        t = threading.Thread(target=submit_skip)
        t.start()

        result = sm.run()
        t.join()

        # Should have reached "done" via skip, not halted
        assert result["final_state"] == "done"
        assert len(approval_calls) == 1
        assert "Quality Score:" in approval_calls[0]["content"]

    def test_circuit_break_abort_halts(self, tmp_path):
        """Circuit breaker with approval_callback halts on 'abort'."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "loop"},
                "loop": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "next": "loop",
                    "transitions": {
                        "proceed": "done",
                    },
                },
                "done": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "circuit_breaker": {
                "rules": [{"name": "state_visit_limit", "limit": 3}]
            },
            "settings": {"timeout_per_agent": 30},
        }
        agents = {"claude": MockAgent(["ok"])}

        def approval_callback(data):
            pass

        sm = StateMachine(
            config,
            agents=agents,
            approval_callback=approval_callback,
        )
        sm.initialize("test-run")

        def submit_abort():
            import time
            for _ in range(100):
                if sm.awaiting_approval:
                    sm.submit_approval("abort")
                    return
                time.sleep(0.05)

        t = threading.Thread(target=submit_abort)
        t.start()

        result = sm.run()
        t.join()

        assert result["final_state"] == "halt"
        assert result.get("user_aborted") is True

    def test_circuit_break_feedback_retries_with_guidance(self, tmp_path):
        """Circuit breaker 'feedback' decision stores user guidance and goes to synthesize."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "loop"},
                "loop": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "next": "loop",
                    "transitions": {"proceed": "done"},
                },
                "synthesize": {
                    "type": "single",
                    "agent": "synth",
                    "output": str(tmp_path / "synth.md"),
                    "transitions": {"success": "done"},
                },
                "done": {"type": "terminal"},
            },
            "circuit_breaker": {
                "rules": [{"name": "state_visit_limit", "limit": 3}]
            },
        }
        agents = {
            "claude": MockAgent(["ok"]),
            "synth": MockAgent(["synthesized"]),
        }

        approval_calls = []

        def approval_callback(data):
            approval_calls.append(data)

        sm = StateMachine(
            config,
            agents=agents,
            approval_callback=approval_callback,
        )
        sm.initialize("test-run")
        sm.run_dir = str(tmp_path)

        def submit_feedback():
            import time
            for _ in range(100):
                if sm.awaiting_approval:
                    sm.submit_approval("feedback", "Make it more conversational")
                    return
                time.sleep(0.05)

        t = threading.Thread(target=submit_feedback)
        t.start()
        result = sm.run()
        t.join()

        # Should have received approval call with quality score
        assert len(approval_calls) == 1
        assert "Quality Score:" in approval_calls[0]["content"]
        # Should have gone to synthesize and then done
        assert result["final_state"] == "done"
        # Synthesize agent should have been called (feedback was used)
        assert agents["synth"].call_count == 1

    def test_circuit_break_includes_audit_results(self, tmp_path):
        """Circuit breaker popup includes audit feedback from auditors."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "loop"},
                "loop": {
                    "type": "single",
                    "agent": "claude",
                    "output": str(tmp_path / "out.md"),
                    "next": "loop",
                    "transitions": {"proceed": "done"},
                },
                "done": {"type": "terminal"},
            },
            "circuit_breaker": {
                "rules": [{"name": "state_visit_limit", "limit": 3}]
            },
        }
        agents = {"claude": MockAgent(["ok"])}

        approval_data = {}

        def approval_callback(data):
            approval_data.update(data)

        sm = StateMachine(
            config,
            agents=agents,
            approval_callback=approval_callback,
        )
        sm.initialize("test-run")
        sm.run_dir = str(tmp_path)

        # Create audit files that _collect_audit_results will find
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        import json
        (final_dir / "test_final_audit.json").write_text(
            json.dumps({"score": 6, "decision": "retry", "feedback": "Remove em-dashes"})
        )

        def submit_approved():
            import time
            for _ in range(100):
                if sm.awaiting_approval:
                    sm.submit_approval("approved")
                    return
                time.sleep(0.05)

        t = threading.Thread(target=submit_approved)
        t.start()
        sm.run()
        t.join()

        # Verify audit_results were included in the callback
        assert "audit_results" in approval_data
        assert len(approval_data["audit_results"]) == 1
        assert approval_data["audit_results"][0]["feedback"] == "Remove em-dashes"


class TestSynthesizerAuditLoop:
    """Tests for the synthesizer -> final-audit -> synthesize retry loop."""

    def test_final_audit_retry_goes_to_synthesize(self, tmp_path):
        """When final-audit returns 'retry', it should go back to synthesize."""
        config = {
            "states": {
                "start": {"type": "initial", "next": "synthesize"},
                "synthesize": {
                    "type": "single",
                    "agent": "synth",
                    "output": str(tmp_path / "final.md"),
                    "transitions": {"success": "final-audit"},
                },
                "final-audit": {
                    "type": "fan-out",
                    "agents": ["auditor"],
                    "output": str(tmp_path / "{agent}_audit.json"),
                    "output_type": "final_audit",
                    "transitions": {
                        "proceed": "done",
                        "retry": "synthesize",  # Key: retry goes back to synthesize
                        "halt": "halt",
                    },
                },
                "done": {"type": "terminal"},
                "halt": {"type": "terminal"},
            },
            "settings": {"timeout_per_agent": 30},
        }

        # First audit returns retry (score 7), second returns proceed (score 8)
        audit_retry = '{"score": 7, "decision": "retry", "feedback": "Almost there"}'
        audit_proceed = '{"score": 8, "decision": "proceed", "feedback": "Good"}'

        agents = {
            "synth": MockAgent(["draft 1", "draft 2"]),
            "auditor": MockAgent([audit_retry, audit_proceed]),
        }

        sm = StateMachine(config, agents=agents)
        sm.initialize("test-run")
        sm.run_dir = str(tmp_path)

        result = sm.run()

        # Should complete successfully after retry loop
        assert result["final_state"] == "done"
        # Synthesizer should have been called twice
        assert agents["synth"].call_count == 2
        # Auditor should have been called twice
        assert agents["auditor"].call_count == 2
