"""Tests for session management."""

import json
import os
import pytest
from runner.sessions.native import NativeSessionManager


@pytest.fixture
def session_dir(tmp_path):
    """Provide a temporary session directory."""
    return str(tmp_path / "sessions")


class TestNativeSessionManager:
    def test_no_session_initially(self, session_dir):
        manager = NativeSessionManager("claude", session_dir)
        assert not manager.has_session()
        assert manager.session_id is None

    def test_capture_claude_session_id(self, session_dir):
        manager = NativeSessionManager("claude", session_dir)
        output = "Starting session...\nSession ID: abc123-def456\nReady."

        captured = manager.capture_session_id(output)

        assert captured == "abc123-def456"
        assert manager.session_id == "abc123-def456"
        assert manager.has_session()

    def test_capture_gemini_session_id(self, session_dir):
        manager = NativeSessionManager("gemini", session_dir)
        output = '{"session_id": "gem-session-789", "result": "ok"}'

        captured = manager.capture_session_id(output)

        assert captured == "gem-session-789"

    def test_capture_codex_session_id(self, session_dir):
        manager = NativeSessionManager("codex", session_dir)
        output = "Codex CLI v1.0\nSession ID: codex-sess-42\n"

        captured = manager.capture_session_id(output)

        assert captured == "codex-sess-42"

    def test_session_persists_to_file(self, session_dir):
        manager = NativeSessionManager("claude", session_dir)
        manager.capture_session_id("Session ID: persist-test")

        session_file = os.path.join(session_dir, "claude_session.json")
        assert os.path.exists(session_file)

        with open(session_file) as f:
            data = json.load(f)
        assert data["session_id"] == "persist-test"
        assert data["agent"] == "claude"

    def test_session_loads_from_file(self, session_dir):
        os.makedirs(session_dir, exist_ok=True)
        session_file = os.path.join(session_dir, "claude_session.json")
        with open(session_file, "w") as f:
            json.dump({"session_id": "preexisting", "agent": "claude"}, f)

        manager = NativeSessionManager("claude", session_dir)

        assert manager.session_id == "preexisting"
        assert manager.has_session()

    def test_clear_session(self, session_dir):
        manager = NativeSessionManager("claude", session_dir)
        manager.capture_session_id("Session ID: to-clear")
        assert manager.has_session()

        manager.clear_session()

        assert not manager.has_session()
        assert manager.session_id is None

    def test_get_command_without_session(self, session_dir):
        manager = NativeSessionManager("claude", session_dir)
        config = {"command": "claude -p {prompt}"}

        cmd = manager.get_command(config, "Hello world")

        assert "claude -p" in cmd
        assert "Hello world" in cmd or "'Hello world'" in cmd

    def test_get_command_with_session(self, session_dir):
        manager = NativeSessionManager("claude", session_dir)
        manager.session_id = "sess-123"
        config = {
            "command": "claude -p {prompt}",
            "resume_command": "claude --resume {session_id} -p {prompt}",
        }

        cmd = manager.get_command(config, "Follow up")

        assert "--resume" in cmd
        assert "sess-123" in cmd

    def test_shlex_quotes_prompt(self, session_dir):
        manager = NativeSessionManager("claude", session_dir)
        config = {"command": "claude -p {prompt}"}

        cmd = manager.get_command(config, "Test with 'quotes' and $pecial chars")

        assert "'" in cmd or '"' in cmd

    def test_unknown_agent_returns_none(self, session_dir):
        manager = NativeSessionManager("unknown_agent", session_dir)
        output = "Session ID: xyz"

        captured = manager.capture_session_id(output)

        assert captured is None
