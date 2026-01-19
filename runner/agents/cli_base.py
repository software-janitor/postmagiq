"""Base class for CLI-based agents."""

import json
import os
import re
import subprocess
import threading
import time
from typing import Optional

from runner.agents.base import BaseAgent
from runner.models import AgentResult, TokenUsage
from runner.sessions.native import NativeSessionManager


# Patterns indicating rate limiting / capacity issues
RATE_LIMIT_PATTERNS = [
    r"429",
    r"rate.?limit",
    r"too.?many.?requests",
    r"capacity.?exhausted",
    r"RESOURCE_EXHAUSTED",
    r"quota.?exceeded",
    r"overloaded",
]


def _detect_rate_limit(error_text: str) -> bool:
    """Check if error indicates rate limiting."""
    error_lower = error_text.lower()
    for pattern in RATE_LIMIT_PATTERNS:
        if re.search(pattern, error_lower, re.IGNORECASE):
            return True
    return False


class CLIAgent(BaseAgent):
    """Base class for agents that use CLI subprocess invocation."""

    # Retry settings for rate limit errors
    MAX_RATE_LIMIT_RETRIES = 3
    RATE_LIMIT_BACKOFF_BASE = 30  # seconds

    def __init__(self, config: dict, session_dir: str = "workflow/sessions"):
        super().__init__(config)
        self.session_manager = NativeSessionManager(self.name, session_dir)
        self.timeout = config.get("timeout", 300)
        self._current_process: Optional[subprocess.Popen] = None
        self._process_lock = threading.Lock()

    def invoke(self, prompt: str, input_files: Optional[list[str]] = None) -> AgentResult:
        """One-shot invocation without session."""
        full_prompt = self._build_prompt(prompt, input_files)
        return self._execute(full_prompt, use_session=False)

    def invoke_with_session(
        self, session_id: str, prompt: str, input_files: Optional[list[str]] = None
    ) -> AgentResult:
        """Invocation with session context.

        First call creates a new session and captures the ID.
        Subsequent calls resume the existing session.
        """
        # Don't pre-set session_id - let the first call create it
        # Only set if we've already captured a real session from Claude
        full_prompt = self._build_prompt(prompt, input_files)
        return self._execute(full_prompt, use_session=True)

    def _build_prompt(self, prompt: str, input_files: Optional[list[str]] = None) -> str:
        """Build full prompt including file contents if provided."""
        if not input_files:
            return prompt

        file_contents = []
        for path in input_files:
            if os.path.exists(path):
                with open(path) as f:
                    content = f.read()
                file_contents.append(f"## File: {path}\n\n{content}")

        if file_contents:
            return prompt + "\n\n" + "\n\n".join(file_contents)
        return prompt

    def _execute(self, prompt: str, use_session: bool = False) -> AgentResult:
        """Execute CLI command and parse result.

        Uses Popen for killable subprocess - allows external timeout handling
        to actually terminate the process. Retries on rate limit errors.
        """
        start_time = time.time()
        last_error = None

        for attempt in range(self.MAX_RATE_LIMIT_RETRIES + 1):
            result = self._execute_once(prompt, use_session, start_time)

            # If successful or non-rate-limit error, return immediately
            if result.success:
                return result

            if not result.error or "rate limited" not in result.error:
                return result

            # Rate limit hit - retry with backoff
            last_error = result.error
            if attempt < self.MAX_RATE_LIMIT_RETRIES:
                backoff = self.RATE_LIMIT_BACKOFF_BASE * (2 ** attempt)
                print(f"[{self.name}] Rate limited, waiting {backoff}s before retry {attempt + 2}/{self.MAX_RATE_LIMIT_RETRIES + 1}...")
                time.sleep(backoff)

        # All retries exhausted
        return AgentResult(
            success=False,
            content="",
            tokens=TokenUsage(input_tokens=0, output_tokens=0),
            duration_s=time.time() - start_time,
            error=last_error or "Rate limit retries exhausted",
        )

    def _execute_once(self, prompt: str, use_session: bool, start_time: float) -> AgentResult:
        """Execute a single CLI invocation."""
        try:
            args = self._get_command_args(prompt, use_session)

            with self._process_lock:
                self._current_process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            try:
                stdout, stderr = self._current_process.communicate(timeout=self.timeout)
                returncode = self._current_process.returncode
            finally:
                with self._process_lock:
                    self._current_process = None

            duration = time.time() - start_time

            if returncode != 0:
                error_text = stderr or f"Exit code {returncode}"

                # Detect rate limiting and provide cleaner error message
                if _detect_rate_limit(error_text):
                    error_text = f"model '{self.name}' is rate limited (out of capacity)"

                return AgentResult(
                    success=False,
                    content="",
                    tokens=TokenUsage(input_tokens=0, output_tokens=0),
                    duration_s=duration,
                    error=error_text,
                )

            content, tokens = self._parse_output(stdout)

            if not self.session_manager.has_session() and use_session:
                self.session_manager.capture_session_id(stdout)

            return AgentResult(
                success=True,
                content=content,
                tokens=tokens,
                duration_s=duration,
                session_id=self.session_manager.session_id,
                cost_usd=self.calculate_cost(tokens),
            )

        except subprocess.TimeoutExpired:
            self.kill()  # Actually kill the subprocess
            return AgentResult(
                success=False,
                content="",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
                duration_s=self.timeout,
                error=f"Timeout after {self.timeout}s",
            )
        except Exception as e:
            self.kill()  # Clean up on any error
            return AgentResult(
                success=False,
                content="",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
                duration_s=time.time() - start_time,
                error=str(e),
            )

    def kill(self) -> bool:
        """Kill the currently running subprocess if any.

        Returns True if a process was killed, False otherwise.
        Thread-safe - can be called from timeout handler in another thread.
        """
        with self._process_lock:
            if self._current_process is not None:
                try:
                    self._current_process.terminate()
                    try:
                        self._current_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._current_process.kill()
                        self._current_process.wait()
                    return True
                except Exception:
                    pass
            return False

    def _get_command_args(self, prompt: str, use_session: bool) -> list[str]:
        """Get command as args list. Override in subclasses."""
        raise NotImplementedError

    def _parse_output(self, stdout: str) -> tuple[str, TokenUsage]:
        """Parse CLI output to extract content and tokens. Override in subclasses."""
        raise NotImplementedError

    def extract_tokens(self, raw_response: str) -> TokenUsage:
        """Extract token counts from raw response."""
        _, tokens = self._parse_output(raw_response)
        return tokens

    def supports_native_session(self) -> bool:
        return True

    @property
    def session_type(self) -> str:
        return "native"
