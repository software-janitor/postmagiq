"""Developer logging for LLM message visibility.

When DEV_MODE is enabled, logs full LLM request/response payloads
to files and optionally broadcasts them via callback.
"""

import json
import os
from datetime import datetime
from typing import Callable, Optional


class DevLogger:
    """Logs detailed LLM request/response for debugging.

    Writes to: workflow/runs/{run_id}/dev_logs/llm_messages.jsonl
    """

    def __init__(
        self,
        run_dir: str,
        broadcast_callback: Optional[Callable[[dict], None]] = None,
        enabled: bool = True,
    ):
        """Initialize dev logger.

        Args:
            run_dir: Run directory (e.g., workflow/runs/2026-01-26_post_04_abc123)
            broadcast_callback: Optional callback to broadcast events (for WebSocket)
            enabled: Whether dev logging is enabled
        """
        self.run_dir = run_dir
        self.broadcast_callback = broadcast_callback
        self.enabled = enabled

        if enabled:
            self.dev_logs_dir = os.path.join(run_dir, "dev_logs")
            os.makedirs(self.dev_logs_dir, exist_ok=True)
            self.log_file = os.path.join(self.dev_logs_dir, "llm_messages.jsonl")
        else:
            self.dev_logs_dir = None
            self.log_file = None

    def log_llm_request(
        self,
        run_id: str,
        state: str,
        agent: str,
        model: str,
        system_prompt: Optional[str],
        user_message: str,
        context_window: int,
        estimated_tokens: Optional[int] = None,
    ) -> None:
        """Log an LLM request before it's sent.

        Args:
            run_id: Workflow run ID
            state: Current state name
            agent: Agent name (e.g., "claude", "ollama")
            model: Model ID being used
            system_prompt: System prompt (if any)
            user_message: User message content
            context_window: Max context window for this model
            estimated_tokens: Estimated input tokens (if available)
        """
        if not self.enabled:
            return

        timestamp = datetime.utcnow().isoformat() + "Z"

        entry = {
            "ts": timestamp,
            "event": "llm:request",
            "run_id": run_id,
            "state": state,
            "agent": agent,
            "model": model,
            "system_prompt": system_prompt,
            "user_message": user_message,
            "context_window": context_window,
            "estimated_tokens": estimated_tokens,
        }

        # Check if we're approaching context limit
        if estimated_tokens and context_window:
            usage_percent = (estimated_tokens / context_window) * 100
            entry["context_usage_percent"] = round(usage_percent, 1)
            if usage_percent > 80:
                entry["context_warning"] = f"High context usage: {usage_percent:.1f}%"

        # Write to file
        self._write_entry(entry)

        # Broadcast via callback
        if self.broadcast_callback:
            # Create broadcast payload (same structure but typed for WebSocket)
            broadcast_entry = {
                "type": "llm:request",
                "run_id": run_id,
                "state": state,
                "agent": agent,
                "model": model,
                "system_prompt": system_prompt,
                "user_message": user_message,
                "context_window": context_window,
                "estimated_tokens": estimated_tokens,
                "context_usage_percent": entry.get("context_usage_percent"),
                "context_warning": entry.get("context_warning"),
                "timestamp": timestamp,
            }
            self.broadcast_callback(broadcast_entry)

    def log_llm_response(
        self,
        run_id: str,
        state: str,
        agent: str,
        model: str,
        content: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
        context_window: int,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Log an LLM response after it's received.

        Args:
            run_id: Workflow run ID
            state: Current state name
            agent: Agent name
            model: Model ID used
            content: Response content
            input_tokens: Actual input tokens used
            output_tokens: Output tokens generated
            duration_ms: Response time in milliseconds
            context_window: Max context window for this model
            success: Whether the call succeeded
            error: Error message if failed
        """
        if not self.enabled:
            return

        timestamp = datetime.utcnow().isoformat() + "Z"
        total_tokens = input_tokens + output_tokens

        entry = {
            "ts": timestamp,
            "event": "llm:response",
            "run_id": run_id,
            "state": state,
            "agent": agent,
            "model": model,
            "content": content,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens,
            },
            "duration_ms": duration_ms,
            "context_window": context_window,
            "success": success,
        }

        if error:
            entry["error"] = error

        # Calculate context usage
        if context_window > 0:
            usage_percent = (total_tokens / context_window) * 100
            entry["context_usage_percent"] = round(usage_percent, 1)
            remaining = context_window - total_tokens
            entry["context_remaining"] = remaining

            if usage_percent > 90:
                entry["context_warning"] = f"Critical: {usage_percent:.1f}% context used, {remaining:,} tokens remaining"
            elif usage_percent > 80:
                entry["context_warning"] = f"Warning: {usage_percent:.1f}% context used"

        # Write to file
        self._write_entry(entry)

        # Broadcast via callback
        if self.broadcast_callback:
            broadcast_entry = {
                "type": "llm:response",
                "run_id": run_id,
                "state": state,
                "agent": agent,
                "model": model,
                "content": content,
                "tokens": entry["tokens"],
                "duration_ms": duration_ms,
                "context_window": context_window,
                "context_usage_percent": entry.get("context_usage_percent"),
                "context_remaining": entry.get("context_remaining"),
                "context_warning": entry.get("context_warning"),
                "success": success,
                "error": error,
                "timestamp": timestamp,
            }
            self.broadcast_callback(broadcast_entry)

    def _write_entry(self, entry: dict) -> None:
        """Write entry to JSONL file."""
        if not self.log_file:
            return

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            # Don't let logging failures break the workflow
            pass

    @staticmethod
    def read_log(log_file: str) -> list[dict]:
        """Read dev log entries from file.

        Args:
            log_file: Path to llm_messages.jsonl

        Returns:
            List of log entries
        """
        if not os.path.exists(log_file):
            return []

        entries = []
        with open(log_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries
