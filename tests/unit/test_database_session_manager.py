"""Tests for DatabaseSessionManager."""

import importlib
import pytest
from sqlmodel import SQLModel, create_engine

db_engine = importlib.import_module("runner.db.engine")
from runner.db import models  # noqa: F401
from runner.content.workflow_store import WorkflowStore
from runner.sessions.database import DatabaseSessionManager
from runner.content.ids import get_system_user_id


@pytest.fixture
def test_engine(monkeypatch):
    """Create an in-memory SQLModel engine for tests."""
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db_engine, "engine", engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def store(test_engine):
    """WorkflowStore wired to the test engine."""
    return WorkflowStore()


@pytest.fixture
def user_id(test_engine):
    """Return a system user UUID for session tests."""
    return get_system_user_id()




class TestDatabaseSessionManager:
    """Test database-backed session management."""

    def test_no_session_initially(self, store, user_id):
        """Test that manager starts without a session."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)
        assert manager.session_id is None
        assert not manager.has_session()

    def test_capture_claude_session_id(self, store, user_id):
        """Test capturing Claude session ID from output."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)

        output = 'Some output\nSession ID: abc123-def456\nMore output'
        session_id = manager.capture_session_id(output)

        assert session_id == "abc123-def456"
        assert manager.session_id == "abc123-def456"
        assert manager.has_session()

    def test_capture_claude_json_format(self, store, user_id):
        """Test capturing session ID from JSON output."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)

        output = '{"session_id": "json-session-789", "result": "ok"}'
        session_id = manager.capture_session_id(output)

        assert session_id == "json-session-789"
        assert manager.session_id == "json-session-789"

    def test_session_persists_to_database(self, store, user_id):
        """Test that session is saved to and loaded from database."""
        manager1 = DatabaseSessionManager("claude", store, user_id=user_id)
        manager1.capture_session_id("Session ID: persist-test-123")

        # Create new manager instance - should load from database
        manager2 = DatabaseSessionManager("claude", store, user_id=user_id)
        assert manager2.session_id == "persist-test-123"
        assert manager2.has_session()

    def test_session_scoped_by_run_id(self, store, user_id):
        """Test that sessions are scoped by run_id."""
        manager1 = DatabaseSessionManager("claude", store, user_id=user_id, run_id="run-1")
        manager1.capture_session_id("Session ID: run1-session")

        manager2 = DatabaseSessionManager("claude", store, user_id=user_id, run_id="run-2")
        assert manager2.session_id is None  # Different run_id

        manager3 = DatabaseSessionManager("claude", store, user_id=user_id, run_id="run-1")
        assert manager3.session_id == "run1-session"  # Same run_id

    def test_session_scoped_by_agent(self, store, user_id):
        """Test that sessions are scoped by agent name."""
        manager1 = DatabaseSessionManager("claude", store, user_id=user_id)
        manager1.capture_session_id("Session ID: claude-session")

        manager2 = DatabaseSessionManager("gemini", store, user_id=user_id)
        assert manager2.session_id is None  # Different agent

    def test_clear_session(self, store, user_id):
        """Test clearing a session."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)
        manager.capture_session_id("Session ID: to-clear-123")
        assert manager.has_session()

        manager.clear_session()
        assert not manager.has_session()
        assert manager.session_id is None

        # Verify deleted from database
        manager2 = DatabaseSessionManager("claude", store, user_id=user_id)
        assert not manager2.has_session()

    def test_get_command_without_session(self, store, user_id):
        """Test getting command without session."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)

        config = {
            "command": "claude -p {prompt}",
            "resume_command": "claude --resume {session_id} -p {prompt}",
        }
        cmd = manager.get_command(config, "Test prompt")

        assert "Test prompt" in cmd
        assert "--resume" not in cmd

    def test_get_command_with_session(self, store, user_id):
        """Test getting command with active session."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)
        manager.capture_session_id("Session ID: active-session")

        config = {
            "command": "claude -p {prompt}",
            "resume_command": "claude --resume {session_id} -p {prompt}",
        }
        cmd = manager.get_command(config, "Test prompt")

        assert "--resume" in cmd
        assert "active-session" in cmd
        assert "Test prompt" in cmd

    def test_get_command_args_without_session(self, store, user_id):
        """Test getting command args without session."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)

        config = {
            "command_args": ["claude", "-p", "{prompt}"],
            "resume_command_args": ["claude", "--resume", "{session_id}", "-p", "{prompt}"],
        }
        args = manager.get_command_args(config, "Test prompt")

        assert args == ["claude", "-p", "Test prompt"]

    def test_get_command_args_with_session(self, store, user_id):
        """Test getting command args with active session."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)
        manager.capture_session_id("Session ID: args-session")

        config = {
            "command_args": ["claude", "-p", "{prompt}"],
            "resume_command_args": ["claude", "--resume", "{session_id}", "-p", "{prompt}"],
        }
        args = manager.get_command_args(config, "Test prompt")

        assert args == ["claude", "--resume", "args-session", "-p", "Test prompt"]

    def test_set_run_id(self, store, user_id):
        """Test setting run_id after initialization."""
        manager = DatabaseSessionManager("claude", store, user_id=user_id)
        assert manager.run_id is None

        manager.set_run_id("new-run-id")
        assert manager.run_id == "new-run-id"

    def test_capture_gemini_session_id(self, store, user_id):
        """Test capturing Gemini session ID from output."""
        manager = DatabaseSessionManager("gemini", store, user_id=user_id)

        output = '{"session_id": "gemini-session-456", "response": "hello"}'
        session_id = manager.capture_session_id(output)

        assert session_id == "gemini-session-456"

    def test_capture_codex_session_id(self, store, user_id):
        """Test capturing Codex session ID from output."""
        manager = DatabaseSessionManager("codex", store, user_id=user_id)

        output = "Initialized.\nSession ID: codex-789\nReady."
        session_id = manager.capture_session_id(output)

        assert session_id == "codex-789"

    def test_no_pattern_for_unknown_agent(self, store, user_id):
        """Test that unknown agents don't crash on capture."""
        manager = DatabaseSessionManager("unknown-agent", store, user_id=user_id)

        output = "Session ID: some-session"
        session_id = manager.capture_session_id(output)

        assert session_id is None
        assert not manager.has_session()
