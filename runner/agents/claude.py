"""Claude CLI agent implementation."""

import json
from typing import Optional

from runner.agents.cli_base import CLIAgent
from runner.models import TokenUsage


class ClaudeAgent(CLIAgent):
    """Agent that uses the Claude CLI."""

    # Pricing per 1k tokens by model
    MODEL_PRICING = {
        "opus": {"input": 0.015, "output": 0.075},      # Claude 3 Opus
        "sonnet": {"input": 0.003, "output": 0.015},    # Claude 3.5 Sonnet
        "haiku": {"input": 0.00025, "output": 0.00125}, # Claude 3 Haiku
    }

    def __init__(self, config: dict, session_dir: str = "workflow/sessions"):
        config.setdefault("name", "claude")
        config.setdefault("context_window", 200000)

        # Set pricing based on model
        model = config.get("model", "sonnet")
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING["sonnet"])
        config.setdefault("cost_per_1k", pricing)

        super().__init__(config, session_dir)
        self.model = model

    def _get_command_args(self, prompt: str, use_session: bool) -> list[str]:
        """Build claude CLI command args."""
        args = ["claude", "--output-format", "json"]

        # Add model if specified
        if self.model:
            args.extend(["--model", self.model])

        if use_session and self.session_manager.has_session():
            args.extend(["--resume", self.session_manager.session_id])

        args.extend(["-p", prompt])
        return args

    def _parse_output(self, stdout: str) -> tuple[str, TokenUsage]:
        """Parse Claude CLI JSON output."""
        try:
            data = json.loads(stdout)

            content = data.get("result", data.get("content", ""))
            if isinstance(content, list):
                content = "\n".join(
                    block.get("text", "") for block in content if block.get("type") == "text"
                )

            usage = data.get("usage", {})
            # Claude CLI uses prompt caching - total input includes cached tokens
            input_tokens = (
                usage.get("input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0)
            )
            tokens = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=usage.get("output_tokens", 0),
            )

            return content, tokens

        except json.JSONDecodeError:
            return stdout, TokenUsage(input_tokens=0, output_tokens=0)
