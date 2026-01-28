"""Tests for feedback flow improvements in state machine."""

import os
import threading
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from runner.state_machine import StateMachine
from runner.models import StateResult


def make_config():
    return {
        "states": {
            "start": {"type": "initial", "next": "story-review"},
            "story-review": {
                "type": "single",
                "agent": "mock",
                "persona": "story-reviewer",
                "transitions": {"proceed": "story-process", "retry": "story-feedback"},
            },
            "story-feedback": {
                "type": "human-approval",
                "input": "workflow/review/review_result.json",
                "prompt": "Provide details",
                "transitions": {"feedback": "story-review", "approved": "story-process"},
            },
            "human-approval": {
                "type": "human-approval",
                "input": "workflow/final/final_post.md",
                "prompt": "Approve?",
                "transitions": {"approved": "complete", "feedback": "revise"},
            },
            "revise": {"type": "single", "agent": "mock"},
            "story-process": {"type": "single", "agent": "mock"},
            "complete": {"type": "terminal"},
            "halt": {"type": "terminal"},
        },
        "agents": {},
    }


class TestFeedbackLabeling:
    """Test that feedback is stored with strong USER FEEDBACK labels."""

    def test_feedback_includes_user_label(self, tmp_path):
        """When user provides feedback, it should be labeled as USER FEEDBACK."""
        config = make_config()
        approval_data = {}

        def mock_approval(data):
            approval_data.update(data)

        sm = StateMachine(config, approval_callback=mock_approval)
        sm.run_id = "test-run"

        # Simulate human-approval state execution with feedback
        state = deepcopy(config["states"]["human-approval"])

        # Create a fake file for content
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        final_file = final_dir / "final_post.md"
        final_file.write_text("This is the final post content.")
        sm.run_dir = str(tmp_path)

        # Submit approval in a thread (since _execute_human_approval blocks)
        def submit():
            import time
            time.sleep(0.1)
            sm.submit_approval("feedback", "Change the opening line")

        t = threading.Thread(target=submit)
        t.start()

        result = sm._execute_human_approval(state)
        t.join()

        assert result.transition == "feedback"
        # Check that retry_feedback was stored with strong label
        assert "revise" in sm.retry_feedback
        stored = sm.retry_feedback["revise"]
        assert "USER FEEDBACK" in stored
        assert "Change the opening line" in stored

    def test_feedback_includes_reviewer_context(self, tmp_path):
        """When reviewer content is available, it should be included in feedback."""
        config = make_config()

        def mock_approval(data):
            pass

        sm = StateMachine(config, approval_callback=mock_approval)
        sm.run_id = "test-run"

        state = deepcopy(config["states"]["story-feedback"])

        # Create reviewer output file
        review_dir = tmp_path / "review"
        review_dir.mkdir()
        review_file = review_dir / "review_result.json"
        review_file.write_text('{"questions": ["What error did you see?"]}')
        sm.run_dir = str(tmp_path)

        def submit():
            import time
            time.sleep(0.1)
            sm.submit_approval("feedback", "The error was a segfault in module X")

        t = threading.Thread(target=submit)
        t.start()

        result = sm._execute_human_approval(state)
        t.join()

        assert result.transition == "feedback"
        assert "story-review" in sm.retry_feedback
        stored = sm.retry_feedback["story-review"]
        # Should have both reviewer context and user feedback
        assert "Reviewer Context" in stored
        assert "USER FEEDBACK" in stored
        assert "segfault" in stored

    def test_approval_callback_includes_reviewer_context(self, tmp_path):
        """Approval callback should include reviewer_context field."""
        config = make_config()
        callback_data = {}

        def mock_approval(data):
            callback_data.update(data)

        sm = StateMachine(config, approval_callback=mock_approval)
        sm.run_id = "test-run"

        state = deepcopy(config["states"]["story-feedback"])

        review_dir = tmp_path / "review"
        review_dir.mkdir()
        review_file = review_dir / "review_result.json"
        review_file.write_text('{"questions": ["What tool?"]}')
        sm.run_dir = str(tmp_path)

        def submit():
            import time
            time.sleep(0.1)
            sm.submit_approval("approved")

        t = threading.Thread(target=submit)
        t.start()

        sm._execute_human_approval(state)
        t.join()

        assert "reviewer_context" in callback_data
        assert "What tool?" in callback_data["reviewer_context"]


class TestOllamaMessageSplit:
    """Test that Ollama agent splits prompts correctly on feedback markers."""

    def test_splits_on_user_feedback_marker(self):
        """Prompts with USER FEEDBACK marker should split into system + user messages."""
        prompt = (
            "# Core Rules\n\nZero fabrication.\n\n"
            "# Story Reviewer\n\nReview the story.\n\n"
            "## USER FEEDBACK — MUST INCORPORATE\n\n"
            "The error was a segfault in module X."
        )

        # The split logic looks for markers (same order as ollama.py)
        markers = ["## Input Files", "## Reviewer Context", "## USER FEEDBACK", "## Context", "## File:"]
        system_content = None
        user_content = prompt

        for marker in markers:
            if marker in prompt:
                idx = prompt.find(marker)
                system_content = prompt[:idx].strip()
                user_content = prompt[idx:].strip()
                break

        assert system_content is not None
        assert "Core Rules" in system_content
        assert "Story Reviewer" in system_content
        assert "USER FEEDBACK" in user_content
        assert "segfault" in user_content

    def test_splits_on_reviewer_context_marker(self):
        """When both Reviewer Context and USER FEEDBACK are present,
        Reviewer Context is matched first (earlier in marker list) so both
        end up in the user message."""
        prompt = (
            "# Rules\n\nDon't fabricate.\n\n"
            "## Reviewer Context\n\n"
            '{"questions": ["What tool?"]}\n\n'
            "## USER FEEDBACK — MUST INCORPORATE\n\n"
            "It was pytest."
        )

        markers = ["## Input Files", "## Reviewer Context", "## USER FEEDBACK", "## Context", "## File:"]
        system_content = None
        user_content = prompt

        for marker in markers:
            if marker in prompt:
                idx = prompt.find(marker)
                system_content = prompt[:idx].strip()
                user_content = prompt[idx:].strip()
                break

        assert system_content is not None
        assert "Rules" in system_content
        # Reviewer Context is matched first, so both it and USER FEEDBACK go to user
        assert "What tool?" in user_content
        assert "USER FEEDBACK" in user_content
        assert "pytest" in user_content
