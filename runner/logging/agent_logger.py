"""Agent invocation logging."""

import json
import os
from datetime import datetime
from typing import Optional

from runner.models import TokenUsage


class AgentLogger:
    """Logs agent invocations to JSONL files."""

    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.agent_logs_dir = os.path.join(run_dir, "agent_logs")
        os.makedirs(self.agent_logs_dir, exist_ok=True)

    def _get_log_file(self, agent: str, state: str) -> str:
        """Get log file path for agent/state combination."""
        return os.path.join(self.agent_logs_dir, f"{agent}_{state}.jsonl")

    def log_invoke(
        self,
        agent: str,
        state: str,
        persona: Optional[str] = None,
        input_files: Optional[list[str]] = None,
        prompt: Optional[str] = None,
        command: Optional[str] = None,
    ):
        """Log agent invocation start with full prompt."""
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": "invoke",
            "agent": agent,
            "state": state,
            "persona": persona,
        }

        if input_files:
            entry["input_files"] = input_files

        if prompt:
            # Store full prompt for persona improvement analysis
            entry["prompt"] = prompt
            # Also keep preview for quick scanning
            entry["prompt_preview"] = prompt[:200] + "..." if len(prompt) > 200 else prompt

        if command:
            entry["command"] = command

        log_file = self._get_log_file(agent, state)
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_complete(
        self,
        agent: str,
        state: str,
        success: bool,
        duration_s: float,
        output_path: Optional[str] = None,
        output: Optional[str] = None,
        tokens: Optional[TokenUsage] = None,
        cost_usd: Optional[float] = None,
        error: Optional[str] = None,
    ):
        """Log agent invocation completion with full output."""
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": "complete",
            "agent": agent,
            "state": state,
            "success": success,
            "duration_s": round(duration_s, 2),
        }

        if output_path:
            entry["output_path"] = output_path

        if output:
            # Store full output for persona improvement analysis
            entry["output"] = output
            # Also keep preview for quick scanning
            entry["output_preview"] = output[:200] + "..." if len(output) > 200 else output

        if tokens:
            entry["tokens"] = {
                "input": tokens.input_tokens,
                "output": tokens.output_tokens,
                "total": tokens.total,
            }

        if cost_usd is not None:
            entry["cost_usd"] = round(cost_usd, 4)

        if error:
            entry["error"] = error

        log_file = self._get_log_file(agent, state)
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_agent_log(self, agent: str, state: str) -> list[dict]:
        """Read log entries for a specific agent/state."""
        log_file = self._get_log_file(agent, state)
        if not os.path.exists(log_file):
            return []

        entries = []
        with open(log_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    def list_agent_logs(self) -> list[str]:
        """List all agent log files."""
        if not os.path.exists(self.agent_logs_dir):
            return []
        return [f for f in os.listdir(self.agent_logs_dir) if f.endswith(".jsonl")]
