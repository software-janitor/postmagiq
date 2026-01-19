"""Tests for logging system."""

import pytest
import os
from datetime import datetime

from runner.logging import StateLogger, AgentLogger, SummaryGenerator
from runner.models import TokenUsage, RunManifest
from runner.metrics import TokenTracker


@pytest.fixture
def run_dir(tmp_path):
    return str(tmp_path / "runs" / "test-run-001")


class TestStateLogger:
    def test_creates_log_file(self, run_dir):
        logger = StateLogger(run_dir, "test-run-001")
        logger.log({"event": "test"})

        assert os.path.exists(logger.log_file)

    def test_log_start(self, run_dir):
        logger = StateLogger(run_dir, "test-run-001")
        logger.log_start("post_03", config_hash="abc123")

        entries = logger.read_log()
        assert len(entries) == 1
        assert entries[0]["event"] == "workflow_start"
        assert entries[0]["story"] == "post_03"

    def test_log_state_enter(self, run_dir):
        logger = StateLogger(run_dir, "test-run-001")
        logger.log_state_enter("draft", "fan-out", has_feedback=True)

        entries = logger.read_log()
        assert entries[0]["state"] == "draft"
        assert entries[0]["type"] == "fan-out"
        assert entries[0]["has_retry_feedback"] is True

    def test_log_transition(self, run_dir):
        logger = StateLogger(run_dir, "test-run-001")
        logger.log_transition("draft", "audit")

        entries = logger.read_log()
        assert entries[0]["event"] == "transition"
        assert entries[0]["from_state"] == "draft"
        assert entries[0]["to_state"] == "audit"

    def test_log_circuit_break(self, run_dir):
        logger = StateLogger(run_dir, "test-run-001")
        logger.log_circuit_break("state_visit_limit", {"state_visits": {"draft": 3}})

        entries = logger.read_log()
        assert entries[0]["event"] == "circuit_break"
        assert entries[0]["rule"] == "state_visit_limit"

    def test_multiple_entries(self, run_dir):
        logger = StateLogger(run_dir, "test-run-001")
        logger.log_start("post_03")
        logger.log_state_enter("draft", "fan-out")
        logger.log_transition("start", "draft")

        entries = logger.read_log()
        assert len(entries) == 3


class TestAgentLogger:
    def test_log_invoke(self, run_dir):
        logger = AgentLogger(run_dir)
        logger.log_invoke(
            agent="claude",
            state="draft",
            persona="writer",
            input_files=["input.md"],
            prompt="Write a post about...",
        )

        entries = logger.read_agent_log("claude", "draft")
        assert len(entries) == 1
        assert entries[0]["event"] == "invoke"
        assert entries[0]["agent"] == "claude"

    def test_log_complete_success(self, run_dir):
        logger = AgentLogger(run_dir)
        tokens = TokenUsage(input_tokens=100, output_tokens=50)

        logger.log_complete(
            agent="claude",
            state="draft",
            success=True,
            duration_s=12.5,
            output_path="drafts/claude_draft.md",
            output="The GPU hit 94°C...",
            tokens=tokens,
            cost_usd=0.005,
        )

        entries = logger.read_agent_log("claude", "draft")
        assert entries[0]["success"] is True
        assert entries[0]["tokens"]["total"] == 150
        assert entries[0]["cost_usd"] == 0.005

    def test_log_complete_failure(self, run_dir):
        logger = AgentLogger(run_dir)

        logger.log_complete(
            agent="claude",
            state="draft",
            success=False,
            duration_s=5.0,
            error="Timeout after 300s",
        )

        entries = logger.read_agent_log("claude", "draft")
        assert entries[0]["success"] is False
        assert "Timeout" in entries[0]["error"]

    def test_list_agent_logs(self, run_dir):
        logger = AgentLogger(run_dir)
        logger.log_invoke("claude", "draft")
        logger.log_invoke("gemini", "draft")
        logger.log_invoke("claude", "audit")

        logs = logger.list_agent_logs()

        assert len(logs) == 3
        assert "claude_draft.jsonl" in logs
        assert "gemini_draft.jsonl" in logs
        assert "claude_audit.jsonl" in logs


class TestSummaryGenerator:
    def test_generate_basic_summary(self, run_dir):
        generator = SummaryGenerator(run_dir, "test-run-001")
        manifest = RunManifest(
            run_id="test-run-001",
            story="post_03",
            started_at=datetime.utcnow(),
            status="complete",
            final_state="complete",
        )

        summary = generator.generate(manifest)

        assert "# Workflow Run: test-run-001" in summary
        assert "post_03" in summary
        assert "complete" in summary

    def test_generate_with_tokens(self, run_dir):
        generator = SummaryGenerator(run_dir, "test-run-001")
        manifest = RunManifest(
            run_id="test-run-001",
            story="post_03",
            started_at=datetime.utcnow(),
            status="complete",
        )

        tracker = TokenTracker("test-run-001")
        tokens = TokenUsage(input_tokens=1000, output_tokens=500)
        tracker.record("claude", "draft", tokens, cost=0.005, context_window=200000)

        summary = generator.generate(manifest, token_summary=tracker.get_summary())

        assert "Token Usage Summary" in summary
        assert "claude" in summary
        assert "1,000" in summary or "1000" in summary

    def test_generate_with_state_log(self, run_dir):
        generator = SummaryGenerator(run_dir, "test-run-001")
        manifest = RunManifest(
            run_id="test-run-001",
            story="post_03",
            started_at=datetime.utcnow(),
            status="complete",
        )

        state_logger = StateLogger(run_dir, "test-run-001")
        state_logger.log_transition("start", "draft")
        state_logger.log_transition("draft", "audit")

        summary = generator.generate(manifest, state_logger=state_logger)

        assert "State Transitions" in summary
        assert "start → draft" in summary
        assert "draft → audit" in summary

    def test_summary_saved_to_file(self, run_dir):
        generator = SummaryGenerator(run_dir, "test-run-001")
        manifest = RunManifest(
            run_id="test-run-001",
            story="post_03",
            started_at=datetime.utcnow(),
            status="complete",
        )

        generator.generate(manifest)

        assert os.path.exists(generator.summary_file)
        with open(generator.summary_file) as f:
            content = f.read()
        assert "# Workflow Run:" in content

    def test_format_duration(self, run_dir):
        generator = SummaryGenerator(run_dir, "test-run-001")

        assert generator._format_duration(45) == "45.0s"
        assert generator._format_duration(125) == "2m 5s"
        assert generator._format_duration(3725) == "1h 2m"
