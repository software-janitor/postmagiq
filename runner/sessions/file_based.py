"""File-based session management for Ollama.

Ollama doesn't have native --resume support like Claude CLI.
This module stores conversation history in JSON files to maintain
context across multiple invocations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class FileBasedSessionManager:
    """Stores conversation history in JSON files for Ollama.

    Each session is stored as a separate JSON file containing:
    - session_id: Unique identifier
    - created_at: ISO timestamp of creation
    - messages: List of {role, content, timestamp, tokens?}
    - total_tokens: Cumulative token count
    """

    def __init__(self, session_dir: str, max_messages: int = 50):
        """Initialize session manager.

        Args:
            session_dir: Directory to store session files
            max_messages: Maximum messages to keep (older ones trimmed)
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.max_messages = max_messages
        self.session_id: Optional[str] = None

    def create_session(self, session_id: str) -> dict:
        """Create a new session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            Session dict with initial state
        """
        self.session_id = session_id
        session = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
            "total_tokens": 0,
        }
        self._save_session(session)
        return session

    def load_session(self, session_id: str) -> Optional[dict]:
        """Load an existing session.

        Args:
            session_id: Session identifier to load

        Returns:
            Session dict if found, None otherwise
        """
        path = self.session_dir / f"{session_id}.json"
        if not path.exists():
            return None

        try:
            with open(path) as f:
                session = json.load(f)
                self.session_id = session_id
                return session
        except (json.JSONDecodeError, IOError):
            return None

    def has_session(self) -> bool:
        """Check if a session is currently loaded."""
        return self.session_id is not None

    def get_session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self.session_id

    def add_message(
        self,
        role: str,
        content: str,
        tokens: Optional[dict] = None,
    ) -> dict:
        """Add a message to the current session.

        Args:
            role: "user", "assistant", or "system"
            content: Message content
            tokens: Optional token counts {input, output, total}

        Returns:
            Updated session dict
        """
        if not self.session_id:
            raise ValueError("No session loaded. Call create_session or load_session first.")

        session = self.load_session(self.session_id)
        if not session:
            session = self.create_session(self.session_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if tokens:
            message["tokens"] = tokens
            session["total_tokens"] += tokens.get("total", 0)

        session["messages"].append(message)
        session = self._trim_if_needed(session)
        self._save_session(session)
        return session

    def get_context_for_ollama(self) -> list[dict]:
        """Get messages formatted for Ollama chat API.

        Returns:
            List of {role, content} dicts suitable for Ollama API
        """
        if not self.session_id:
            return []

        session = self.load_session(self.session_id)
        if not session:
            return []

        return [
            {"role": m["role"], "content": m["content"]}
            for m in session["messages"]
        ]

    def get_total_tokens(self) -> int:
        """Get total tokens used in current session."""
        if not self.session_id:
            return 0

        session = self.load_session(self.session_id)
        if not session:
            return 0

        return session.get("total_tokens", 0)

    def clear_session(self) -> None:
        """Clear and delete the current session."""
        if self.session_id:
            path = self.session_dir / f"{self.session_id}.json"
            if path.exists():
                path.unlink()
        self.session_id = None

    def list_sessions(self) -> list[str]:
        """List all session IDs in the session directory."""
        return [
            p.stem for p in self.session_dir.glob("*.json")
        ]

    def _trim_if_needed(self, session: dict) -> dict:
        """Keep session within max_messages limit.

        Preserves system messages and keeps most recent non-system messages.

        Args:
            session: Session dict to trim

        Returns:
            Trimmed session dict
        """
        messages = session["messages"]
        if len(messages) <= self.max_messages:
            return session

        # Keep system messages + recent messages
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]
        keep_count = self.max_messages - len(system_msgs)

        session["messages"] = system_msgs + other_msgs[-keep_count:]
        return session

    def _save_session(self, session: dict) -> None:
        """Save session to disk.

        Args:
            session: Session dict to save
        """
        path = self.session_dir / f"{session['session_id']}.json"
        with open(path, "w") as f:
            json.dump(session, f, indent=2)

    def add_system_message(self, content: str) -> dict:
        """Add a system message to the current session.

        System messages are preserved during trimming.

        Args:
            content: System message content

        Returns:
            Updated session dict
        """
        return self.add_message("system", content)
