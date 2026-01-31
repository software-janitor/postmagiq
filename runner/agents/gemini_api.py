"""Gemini API agent using the Google Generative AI SDK."""

import os

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from runner.agents.api_base import APIAgent, RateLimitError
from runner.models import TokenUsage


class GeminiAPIAgent(APIAgent):
    """Gemini agent using the Google Generative AI Python SDK.

    Model aliases:
        - pro: gemini-1.5-pro
        - flash: gemini-1.5-flash
        - flash-8b: gemini-1.5-flash-8b
        - pro-2: gemini-2.0-pro
        - flash-2: gemini-2.0-flash
    """

    MODEL_MAP = {
        "pro": "gemini-1.5-pro",
        "flash": "gemini-1.5-flash",
        "flash-8b": "gemini-1.5-flash-8b",
        "pro-2": "gemini-2.0-pro",
        "flash-2": "gemini-2.0-flash",
    }

    def __init__(self, config: dict):
        super().__init__(config)
        genai.configure(api_key=self.api_key)
        self.model_instance = genai.GenerativeModel(self.model_id)
        self.max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt")

        # Configure generation settings
        self.generation_config = genai.GenerationConfig(
            max_output_tokens=self.max_tokens,
        )

    def _get_api_key_from_env(self) -> str:
        return os.environ.get("GOOGLE_API_KEY", "")

    def _resolve_model_id(self) -> str:
        """Convert model alias to actual model ID."""
        return self.MODEL_MAP.get(self.model, self.model)

    def _call_api(self, messages: list[dict]) -> tuple[str, TokenUsage]:
        """Make API call to Gemini and return (content, tokens)."""
        try:
            # Convert messages to Gemini format
            # Gemini uses 'user' and 'model' roles (not 'assistant')
            gemini_messages = []
            for msg in messages:
                role = msg["role"]
                if role == "assistant":
                    role = "model"
                gemini_messages.append({"role": role, "parts": [msg["content"]]})

            # Start chat with history (all but last message)
            # Then send the last message
            if len(gemini_messages) > 1:
                chat = self.model_instance.start_chat(history=gemini_messages[:-1])
                response = chat.send_message(
                    gemini_messages[-1]["parts"][0],
                    generation_config=self.generation_config,
                )
            else:
                # Single message - just generate content
                content_input = gemini_messages[0]["parts"][0]
                if self.system_prompt:
                    content_input = f"{self.system_prompt}\n\n{content_input}"
                response = self.model_instance.generate_content(
                    content_input,
                    generation_config=self.generation_config,
                )

            # Extract content from response
            content = response.text

            # Extract token usage from response metadata
            # Gemini returns usage in response.usage_metadata
            usage = response.usage_metadata
            tokens = TokenUsage(
                input_tokens=usage.prompt_token_count if usage else 0,
                output_tokens=usage.candidates_token_count if usage else 0,
            )

            return content, tokens

        except ResourceExhausted as e:
            raise RateLimitError(str(e))
