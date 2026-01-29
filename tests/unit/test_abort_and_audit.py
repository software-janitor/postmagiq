"""Tests for abort mechanism and audit results in approval callback."""

import json
import os
import threading
import time
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from runner.state_machine import StateMachine
from runner.models import AgentResult, FanOutResult, StateResult, TokenUsage


def make_config():
    return {
        "states": {
            "start": {"type": "initial", "next": "draft"},
            "draft": {
                "type": "fan-out",
                "agents": ["writer_a"],
                "output": "workflow/drafts/{agent}_draft.md",
                "transitions": {"all_success": "audit"},
            },
            "audit": {
                "type": "fan-out",
                "agents": ["auditor_a"],
                "output_type": "audit",
                "output": "workflow/audits/{agent}_audit.json",
                "transitions": {"proceed": "human-approval", "retry": "draft", "halt": "halt"},
            },
            "human-approval": {
                "type": "human-approval",
                "input": "workflow/final/final_post.md",
                "prompt": "Approve?",
                "transitions": {"approved": "complete", "feedback": "draft", "abort": "halt"},
            },
            "complete": {"type": "terminal"},
            "halt": {"type": "terminal"},
        },
        "agents": {},
    }


class TestAbortMechanism:
    """Test abort() stops the state machine."""

    def test_abort_flag_initially_false(self):
        sm = StateMachine(make_config())
        assert sm._aborted is False

    def test_abort_sets_flag(self):
        sm = StateMachine(make_config())
        sm.abort()
        assert sm._aborted is True

    def test_initialize_resets_aborted(self):
        sm = StateMachine(make_config())
        sm.abort()
        assert sm._aborted is True
        sm.initialize("test-run")
        assert sm._aborted is False

    def test_abort_unblocks_pause(self):
        sm = StateMachine(make_config())
        sm.initialize("test-run")
        sm.current_state = "draft"  # pause() requires current_state to be set
        sm.pause()
        assert sm._paused is True

        # Abort should set the pause event so wait() unblocks
        sm.abort()
        assert sm._aborted is True
        assert sm._pause_event.is_set()

    def test_abort_unblocks_approval_wait(self):
        sm = StateMachine(make_config())
        sm.initialize("test-run")

        # Simulate waiting for approval
        sm._approval_event.clear()
        sm.awaiting_approval = True

        sm.abort()
        # The approval event should be set so _wait_for_approval unblocks
        assert sm._approval_event.is_set()

    def test_run_returns_halt_when_aborted_before_start(self):
        """If aborted before run starts iterating, it should return immediately."""
        config = make_config()
        logs = []
        sm = StateMachine(config, log_callback=lambda x: logs.append(x))
        sm.initialize("test-run")
        sm.abort()

        result = sm.run("start")
        assert result["final_state"] == "halt"
        assert result["error"] == "Aborted by user"

    def test_abort_during_pause_returns_halt(self):
        """If paused and then aborted, should return halt."""
        config = make_config()
        logs = []
        sm = StateMachine(config, log_callback=lambda x: logs.append(x))
        sm.initialize("test-run")

        # Make the first state (start) succeed, then pause before draft
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = AgentResult(
            success=True, content="draft content", tokens=TokenUsage(input_tokens=0, output_tokens=0)
        )
        sm.agents["writer_a"] = mock_agent

        # Abort after a short delay
        def abort_after_pause():
            time.sleep(0.2)
            sm.abort()

        # Pause immediately
        sm._paused = True
        sm._pause_event.clear()

        t = threading.Thread(target=abort_after_pause)
        t.start()

        result = sm.run("start")
        t.join()

        assert result["final_state"] == "halt"
        assert result["error"] == "Aborted by user"

    def test_abort_during_approval_wait(self):
        """If waiting for approval and abort is called, should return abort decision."""
        config = make_config()
        sm = StateMachine(config, log_callback=lambda x: None)
        sm.initialize("test-run")

        def abort_shortly():
            time.sleep(0.1)
            sm.abort()

        t = threading.Thread(target=abort_shortly)
        t.start()

        decision, feedback = sm._wait_for_approval(timeout=5)
        t.join()

        assert decision == "abort"
        assert feedback is None


class TestCollectAuditResults:
    """Test _collect_audit_results and _try_parse_audit_json."""

    def test_try_parse_audit_json_valid(self):
        sm = StateMachine(make_config())
        content = json.dumps({"score": 8, "decision": "proceed", "feedback": "Good work"})
        result = sm._try_parse_audit_json(content)
        assert result == {"score": 8, "decision": "proceed", "feedback": "Good work"}

    def test_try_parse_audit_json_with_fence(self):
        sm = StateMachine(make_config())
        content = '```json\n{"score": 5, "decision": "retry", "feedback": "Needs revision"}\n```'
        result = sm._try_parse_audit_json(content)
        assert result["score"] == 5
        assert result["decision"] == "retry"

    def test_try_parse_audit_json_invalid(self):
        sm = StateMachine(make_config())
        result = sm._try_parse_audit_json("not json at all")
        assert result is None

    def test_try_parse_audit_json_extra_braces(self):
        """LLMs sometimes add extra closing braces - should still parse."""
        sm = StateMachine(make_config())
        # Double closing brace
        content = '{"score": 8, "decision": "proceed", "feedback": "Good"}}'
        result = sm._try_parse_audit_json(content)
        assert result is not None
        assert result["score"] == 8
        assert result["decision"] == "proceed"

    def test_try_parse_audit_json_triple_braces(self):
        """Handle triple closing braces."""
        sm = StateMachine(make_config())
        content = '{"score": 7, "decision": "retry", "feedback": "Needs work"}}}'
        result = sm._try_parse_audit_json(content)
        assert result is not None
        assert result["score"] == 7

    def test_extract_json_extra_braces_in_fence(self):
        """Handle extra braces inside markdown fence."""
        sm = StateMachine(make_config())
        content = '```json\n{"score": 9, "decision": "proceed", "feedback": "Great"}}}\n```'
        result = sm._try_parse_audit_json(content)
        assert result is not None
        assert result["score"] == 9

    def test_collect_audit_results_from_files(self, tmp_path):
        sm = StateMachine(make_config())
        sm.run_dir = str(tmp_path)
        sm.run_id = "test-run"

        # Create final audit files
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        audit_data = {"score": 7, "decision": "proceed", "feedback": "Looks good"}
        (final_dir / "auditor_a_final_audit.json").write_text(json.dumps(audit_data))

        results = sm._collect_audit_results()
        assert len(results) == 1
        assert results[0]["agent"] == "auditor_a"
        assert results[0]["score"] == 7
        assert results[0]["decision"] == "proceed"
        assert results[0]["audit_type"] == "final_audit"

    def test_collect_audit_results_from_cross_audit_files(self, tmp_path):
        sm = StateMachine(make_config())
        sm.run_dir = str(tmp_path)
        sm.run_id = "test-run"

        # Create cross-audit files (no final audit)
        audits_dir = tmp_path / "audits"
        audits_dir.mkdir()
        audit_data = {"score": 4, "decision": "retry", "feedback": "Needs work"}
        (audits_dir / "auditor_a_audit.json").write_text(json.dumps(audit_data))

        results = sm._collect_audit_results()
        assert len(results) == 1
        assert results[0]["audit_type"] == "audit"
        assert results[0]["score"] == 4

    def test_collect_audit_results_prefers_final_over_cross(self, tmp_path):
        """Final audit results should be returned, not cross-audit."""
        sm = StateMachine(make_config())
        sm.run_dir = str(tmp_path)
        sm.run_id = "test-run"

        # Create both types
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        (final_dir / "a_final_audit.json").write_text(
            json.dumps({"score": 9, "decision": "proceed", "feedback": "Great"})
        )

        audits_dir = tmp_path / "audits"
        audits_dir.mkdir()
        (audits_dir / "a_audit.json").write_text(
            json.dumps({"score": 3, "decision": "retry", "feedback": "Bad"})
        )

        results = sm._collect_audit_results()
        assert len(results) == 1
        assert results[0]["audit_type"] == "final_audit"
        assert results[0]["score"] == 9

    def test_collect_audit_results_from_database(self):
        """When database has audit outputs, use those."""
        sm = StateMachine(make_config())
        sm.run_id = "test-run"

        mock_output = MagicMock()
        mock_output.content = json.dumps({"score": 6, "decision": "retry", "feedback": "Fix issues"})
        mock_output.agent = "auditor_x"

        mock_db = MagicMock()
        mock_db.get_workflow_outputs_by_type.return_value = [mock_output]
        sm.db = mock_db

        results = sm._collect_audit_results()
        assert len(results) == 1
        assert results[0]["agent"] == "auditor_x"
        assert results[0]["score"] == 6

    def test_collect_audit_results_empty(self, tmp_path):
        sm = StateMachine(make_config())
        sm.run_dir = str(tmp_path)
        sm.run_id = "test-run"
        results = sm._collect_audit_results()
        assert results == []


class TestApprovalCallbackIncludesAuditResults:
    """Test that _execute_human_approval passes audit_results in callback data."""

    def test_approval_callback_includes_audit_results(self, tmp_path):
        config = make_config()
        callback_data = {}

        def capture_callback(data):
            callback_data.update(data)

        sm = StateMachine(config, approval_callback=capture_callback)
        sm.run_id = "test-run"
        sm.run_dir = str(tmp_path)

        # Create content for approval
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        (final_dir / "final_post.md").write_text("Post content here")

        # Create audit files
        (final_dir / "aud_final_audit.json").write_text(
            json.dumps({"score": 8, "decision": "proceed", "feedback": "Nice"})
        )

        # Submit approval in a thread
        def submit():
            time.sleep(0.1)
            sm.submit_approval("approved")

        t = threading.Thread(target=submit)
        t.start()

        state = deepcopy(config["states"]["human-approval"])
        sm._execute_human_approval(state)
        t.join()

        assert "audit_results" in callback_data
        assert len(callback_data["audit_results"]) == 1
        assert callback_data["audit_results"][0]["score"] == 8

    def test_approval_callback_no_audit_results_when_none_available(self, tmp_path):
        config = make_config()
        callback_data = {}

        def capture_callback(data):
            callback_data.update(data)

        sm = StateMachine(config, approval_callback=capture_callback)
        sm.run_id = "test-run"
        sm.run_dir = str(tmp_path)

        # Create content for approval but no audits
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        (final_dir / "final_post.md").write_text("Post content here")

        def submit():
            time.sleep(0.1)
            sm.submit_approval("approved")

        t = threading.Thread(target=submit)
        t.start()

        state = deepcopy(config["states"]["human-approval"])
        sm._execute_human_approval(state)
        t.join()

        # audit_results should not be present when empty
        assert "audit_results" not in callback_data
