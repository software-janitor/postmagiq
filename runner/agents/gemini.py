"""Gemini CLI agent implementation."""

import json
from typing import Optional

from runner.agents.cli_base import CLIAgent
from runner.models import TokenUsage


class GeminiAgent(CLIAgent):
    """Agent that uses the Gemini CLI."""

    # Pricing per 1k tokens by model family
    # Gemini Pro has tiered pricing: $2/$12 (<=200k) and $4/$18 (>200k) - using average
    MODEL_PRICING = {
        "pro": {"input": 0.003, "output": 0.015},        # Gemini 2.5 Pro: avg $3/$15 per M
        "flash": {"input": 0.000075, "output": 0.0003},  # Gemini Flash: $0.075/$0.30 per M
    }

    def __init__(self, config: dict, session_dir: str = "workflow/sessions"):
        config.setdefault("name", "gemini")
        config.setdefault("context_window", 1000000)

        # Determine model family from name for pricing
        name = config.get("name", "gemini")
        if "flash" in name.lower():
            pricing = self.MODEL_PRICING["flash"]
        else:
            # Default to Pro pricing (most expensive = safe default)
            pricing = self.MODEL_PRICING["pro"]
        config.setdefault("cost_per_1k", pricing)

        super().__init__(config, session_dir)
        self.model = config.get("model")  # e.g., "gemini-2.0-flash", "gemini-1.5-pro"

    def _get_command_args(self, prompt: str, use_session: bool) -> list[str]:
        """Build gemini CLI command args."""
        args = ["gemini", "--output-format", "json"]

        # Add model if specified
        if self.model:
            args.extend(["-m", self.model])

        if use_session and self.session_manager.has_session():
            args.extend(["--resume", self.session_manager.session_id])

        args.append(prompt)
        return args

    def _parse_output(self, stdout: str) -> tuple[str, TokenUsage]:
        """Parse Gemini CLI JSON output."""
        try:
            data = json.loads(stdout)

            # Gemini CLI uses "response" field
            content = data.get("response", data.get("text", data.get("content", "")))
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)

            total_input = 0
            total_output = 0

            # Format 1: usageMetadata (direct API response format)
            usage_metadata = data.get("usageMetadata", {})
            if usage_metadata:
                total_input = usage_metadata.get("promptTokenCount", 0)
                total_output = usage_metadata.get("candidatesTokenCount", 0)
            else:
                # Format 2: stats.models (CLI format)
                stats = data.get("stats", {})
                models = stats.get("models", {})
                for model_stats in models.values():
                    tokens = model_stats.get("tokens", {})
                    total_input += tokens.get("input", 0)
                    total_output += tokens.get("candidates", 0)

            tokens = TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
            )

            return content, tokens

        except json.JSONDecodeError:
            return stdout, TokenUsage(input_tokens=0, output_tokens=0)
