"""Session management for CLI agents with native --resume support."""

import json
import os
import re
import shlex
from typing import Optional


class NativeSessionManager:
    """For agents with built-in --resume support (Claude, Gemini, Codex)."""

    SESSION_PATTERNS = {
        # Claude: "session_id": "xxx", "sessionId": "xxx", or "Session ID: xxx"
        "claude": r'["\']?[sS]ession[\s_]?[iI][dD]["\']?\s*[:\s]+["\']?([a-zA-Z0-9_-]+)["\']?',
        "gemini": r'session_id["\']?:\s*["\']?([^"\',\s}]+)',
        "codex": r"Session\s+ID:\s*(\S+)",
    }

    def __init__(self, agent_name: str, session_dir: str):
        self.agent_name = agent_name
        self.session_dir = session_dir
        self.session_file = os.path.join(session_dir, f"{agent_name}_session.json")
        self.session_id: Optional[str] = self._load_session_id()

    def _load_session_id(self) -> Optional[str]:
        """Load persisted session ID if exists."""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file) as f:
                    return json.load(f).get("session_id")
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def capture_session_id(self, cli_output: str) -> Optional[str]:
        """Parse CLI output to extract real session ID.

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
        """Save session ID to disk for resume across runs."""
        os.makedirs(self.session_dir, exist_ok=True)
        with open(self.session_file, "w") as f:
            json.dump(
                {"session_id": self.session_id, "agent": self.agent_name}, f, indent=2
            )

    def has_session(self) -> bool:
        """Check if we have a valid session ID."""
        return self.session_id is not None

    def get_command(self, agent_config: dict, prompt: str) -> str:
        """Get command - uses resume_command from config if session exists.

        Uses shlex.quote() to prevent shell injection.
        """
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

        return [
            arg.format(prompt=prompt, session_id=self.session_id) for arg in template
        ]

    def clear_session(self):
        """Clear session (e.g., when starting a new workflow run)."""
        self.session_id = None
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
