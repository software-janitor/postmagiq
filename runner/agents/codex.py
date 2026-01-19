"""Codex CLI agent implementation."""

import json
from typing import Optional

from runner.agents.cli_base import CLIAgent
from runner.models import TokenUsage


class CodexAgent(CLIAgent):
    """Agent that uses the Codex/OpenAI CLI."""

    def __init__(self, config: dict, session_dir: str = "workflow/sessions"):
        config.setdefault("name", "codex")
        config.setdefault("context_window", 128000)
        config.setdefault("cost_per_1k", {"input": 0.005, "output": 0.015})
        super().__init__(config, session_dir)
        self.model = config.get("model")  # e.g., "gpt-5.2", "gpt-5.2-codex"
        self.reasoning_effort = config.get("reasoning_effort")  # low, medium, high

    def _get_command_args(self, prompt: str, use_session: bool) -> list[str]:
        """Build codex CLI command args."""
        # Use exec mode for non-interactive execution
        # Note: --json is deprecated but --experimental-json doesn't include token counts
        args = ["codex", "exec", "--json"]

        # Add model if specified
        if self.model:
            args.extend(["-m", self.model])

        # Add reasoning effort if specified
        if self.reasoning_effort:
            args.extend(["-c", f"model_reasoning_effort={self.reasoning_effort}"])

        if use_session and self.session_manager.has_session():
            args.extend(["--resume", self.session_manager.session_id])

        args.append(prompt)
        return args

    def _parse_output(self, stdout: str) -> tuple[str, TokenUsage]:
        """Parse Codex CLI JSON output.

        Codex CLI outputs streaming NDJSON (one JSON object per line).
        Format includes:
        - {"type":"item.completed","item":{"item_type":"assistant_message","text":"..."}}
        - {"type":"token_count","info":{"total_token_usage":{...}}}
        - Legacy: {"type":"agent_message","message":"..."}
        """
        content_parts = []
        input_tokens = 0
        output_tokens = 0

        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue

            try:
                data = json.loads(line)

                # Handle streaming format (with "msg" wrapper for older format)
                msg = data.get("msg", data)
                msg_type = msg.get("type", "")

                # New format: item.completed with type inside item
                if msg_type == "item.completed":
                    item = msg.get("item", {})
                    item_type = item.get("type", "")
                    # Only extract agent_message, skip reasoning
                    if item_type == "agent_message":
                        text = item.get("text", "")
                        if text:
                            content_parts.append(text)

                # Legacy format: agent_message at top level
                elif msg_type == "agent_message":
                    message = msg.get("message", "")
                    if message:
                        content_parts.append(message)

                # Token usage from turn.completed
                elif msg_type == "turn.completed":
                    usage = msg.get("usage", {})
                    if usage:
                        # Include cached tokens in input count
                        input_tokens = (
                            usage.get("input_tokens", 0)
                            + usage.get("cached_input_tokens", 0)
                        )
                        output_tokens = usage.get("output_tokens", 0)

                # Legacy token usage from token_count
                elif msg_type == "token_count":
                    info = msg.get("info", {})
                    if info:
                        usage = info.get("total_token_usage", {})
                        # Include cached tokens in input count
                        input_tokens = (
                            usage.get("input_tokens", 0)
                            + usage.get("cached_input_tokens", 0)
                        )
                        output_tokens = usage.get("output_tokens", 0) + usage.get("reasoning_output_tokens", 0)

                # Handle legacy single-object format
                elif "response" in data or "content" in data or "text" in data:
                    content = data.get("response", data.get("content", data.get("text", "")))
                    if isinstance(content, list):
                        content = "\n".join(str(item) for item in content)
                    if content:
                        content_parts.append(content)

                    usage = data.get("usage", {})
                    input_tokens = usage.get("prompt_tokens", input_tokens)
                    output_tokens = usage.get("completion_tokens", output_tokens)

            except json.JSONDecodeError:
                # Non-JSON line - skip warnings and info messages
                pass

        content = "\n".join(content_parts) if content_parts else stdout
        tokens = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)

        return content, tokens
