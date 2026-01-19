"""Database-backed session management for CLI agents.

Uses SQLModel-backed persistence instead of JSON files for session storage.
This provides better queryability and integrates with the workflow database.
"""

import re
from typing import Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from runner.content.workflow_store import WorkflowStore


class DatabaseSessionManager:
    """Session management using database for persistence.

    Implements the same interface as NativeSessionManager but stores
    session IDs in the database instead of JSON files.
    """

    SESSION_PATTERNS = {
        # Claude: "session_id": "xxx", "sessionId": "xxx", or "Session ID: xxx"
        "claude": r'["\']?[sS]ession[\s_]?[iI][dD]["\']?\s*[:\s]+["\']?([a-zA-Z0-9_-]+)["\']?',
        "gemini": r'session_id["\']?:\s*["\']?([^"\',\s}]+)',
        "codex": r"Session\s+ID:\s*(\S+)",
    }

    def __init__(
        self,
        agent_name: str,
        db: "WorkflowStore",
        user_id: UUID | str,
        run_id: Optional[str] = None,
    ):
        """Initialize database session manager.

        Args:
            agent_name: Name of the agent (claude, gemini, codex)
            db: WorkflowStore instance
            user_id: User ID for the session
            run_id: Optional workflow run ID to scope the session
        """
        self.agent_name = agent_name
        self.db = db
        self.user_id = user_id
        self.run_id = run_id
        self.session_id: Optional[str] = self._load_session_id()

    def _load_session_id(self) -> Optional[str]:
        """Load persisted session ID from database."""
        record = self.db.get_workflow_session(
            self.user_id,
            self.agent_name,
            self.run_id,
        )
        return record.session_id if record else None

    def capture_session_id(self, cli_output: str) -> Optional[str]:
        """Parse CLI output to extract and store session ID.

        Call this after the first invocation to capture the CLI-generated ID.
        """
        pattern = self.SESSION_PATTERNS.get(self.agent_name)
        if not pattern:
            return None

        match = re.search(pattern, cli_output, re.IGNORECASE)
        if match:
            self.session_id = match.group(1)
            self._persist_session_id()
            return self.session_id
        return None

    def _persist_session_id(self):
        """Save session ID to database."""
        if self.session_id:
            self.db.save_workflow_session(
                user_id=self.user_id,
                agent_name=self.agent_name,
                session_id=self.session_id,
                run_id=self.run_id,
            )

    def has_session(self) -> bool:
        """Check if we have a valid session ID."""
        return self.session_id is not None

    def get_command(self, agent_config: dict, prompt: str) -> str:
        """Get command - uses resume_command from config if session exists.

        Uses shlex.quote() to prevent shell injection.
        """
        import shlex
        safe_prompt = shlex.quote(prompt)

        if not self.session_id:
            return agent_config["command"].format(prompt=safe_prompt)

        return agent_config["resume_command"].format(
            session_id=self.session_id, prompt=safe_prompt
        )

    def get_command_args(self, agent_config: dict, prompt: str) -> list[str]:
        """Get command as args list (preferred - no shell needed).

        Returns list suitable for subprocess.run(args, shell=False).
        """
        if not self.session_id:
            template = agent_config.get("command_args", [])
        else:
            template = agent_config.get("resume_command_args", [])

        return [arg.format(prompt=prompt, session_id=self.session_id) for arg in template]

    def clear_session(self):
        """Clear session (e.g., when starting a new workflow run)."""
        self.session_id = None
        self.db.delete_workflow_session(
            self.user_id,
            self.agent_name,
            self.run_id,
        )

    def set_run_id(self, run_id: str):
        """Update the run_id for this session manager.

        Useful when starting a new workflow run after initialization.
        """
        self.run_id = run_id
