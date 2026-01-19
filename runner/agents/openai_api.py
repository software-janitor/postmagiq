"""OpenAI API agent using the OpenAI SDK."""

import os

from openai import OpenAI, RateLimitError as OpenAIRateLimitError

from runner.agents.api_base import APIAgent, RateLimitError
from runner.models import TokenUsage


class OpenAIAPIAgent(APIAgent):
    """OpenAI agent using the official OpenAI Python SDK.

    Model aliases:
        - gpt4: gpt-4-turbo
        - gpt4o: gpt-4o
        - gpt4o-mini: gpt-4o-mini
        - o1: o1
        - o1-mini: o1-mini
        - o3-mini: o3-mini
    """

    MODEL_MAP = {
        "gpt4": "gpt-4-turbo",
        "gpt4o": "gpt-4o",
        "gpt4o-mini": "gpt-4o-mini",
        "o1": "o1",
        "o1-mini": "o1-mini",
        "o3-mini": "o3-mini",
    }

    def __init__(self, config: dict):
        super().__init__(config)
        self.client = OpenAI(api_key=self.api_key)
        self.max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt")

    def _get_api_key_from_env(self) -> str:
        return os.environ.get("OPENAI_API_KEY", "")

    def _resolve_model_id(self) -> str:
        """Convert model alias to actual model ID."""
        return self.MODEL_MAP.get(self.model, self.model)

    def _call_api(self, messages: list[dict]) -> tuple[str, TokenUsage]:
        """Make API call to OpenAI and return (content, tokens)."""
        try:
            # Prepend system message if configured
            api_messages = messages.copy()
            if self.system_prompt:
                api_messages = [
                    {"role": "system", "content": self.system_prompt}
                ] + api_messages

            # o1/o3 models don't support max_tokens, use max_completion_tokens
            is_reasoning_model = self.model_id.startswith(("o1", "o3"))

            kwargs = {
                "model": self.model_id,
                "messages": api_messages,
            }

            if is_reasoning_model:
                kwargs["max_completion_tokens"] = self.max_tokens
            else:
                kwargs["max_tokens"] = self.max_tokens

            response = self.client.chat.completions.create(**kwargs)

            # Extract content from response
            content = response.choices[0].message.content or ""

            # Extract token usage
            tokens = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

            return content, tokens

        except OpenAIRateLimitError as e:
            raise RateLimitError(str(e))
