"""Claude API agent using the Anthropic SDK."""

import os

from anthropic import Anthropic, RateLimitError as AnthropicRateLimitError

from runner.agents.api_base import APIAgent, RateLimitError
from runner.models import TokenUsage


class ClaudeAPIAgent(APIAgent):
    """Claude agent using the official Anthropic Python SDK.

    Model aliases:
        - opus: claude-opus-4-20250514
        - sonnet: claude-sonnet-4-20250514
        - haiku: claude-3-5-haiku-20241022
    """

    MODEL_MAP = {
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-3-5-haiku-20241022",
        # Legacy model names for backwards compatibility
        "claude-3-opus": "claude-opus-4-20250514",
        "claude-3-sonnet": "claude-sonnet-4-20250514",
        "claude-3-haiku": "claude-3-5-haiku-20241022",
    }

    def __init__(self, config: dict):
        super().__init__(config)
        self.client = Anthropic(api_key=self.api_key)
        self.max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt")

    def _get_api_key_from_env(self) -> str:
        return os.environ.get("ANTHROPIC_API_KEY", "")

    def _resolve_model_id(self) -> str:
        """Convert model alias to actual model ID."""
        return self.MODEL_MAP.get(self.model, self.model)

    def _call_api(self, messages: list[dict]) -> tuple[str, TokenUsage]:
        """Make API call to Claude and return (content, tokens)."""
        try:
            kwargs = {
                "model": self.model_id,
                "max_tokens": self.max_tokens,
                "messages": messages,
            }

            if self.system_prompt:
                kwargs["system"] = self.system_prompt

            response = self.client.messages.create(**kwargs)

            # Extract content from response
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            # Extract token usage
            tokens = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            return content, tokens

        except AnthropicRateLimitError as e:
            raise RateLimitError(str(e))
