"""Groq API agent using the official Groq Python SDK."""

import os
from typing import Optional

from groq import Groq, RateLimitError as GroqRateLimitError

from runner.agents.api_base import APIAgent, RateLimitError
from runner.models import TokenUsage


class GroqAPIAgent(APIAgent):
    """Groq agent with chat completions and audio transcription.

    Production models only (https://console.groq.com/docs/models):
        - llama-8b: llama-3.1-8b-instant (560 t/s)
        - llama-70b: llama-3.3-70b-versatile (280 t/s)
        - llama-guard: meta-llama/llama-guard-4-12b (1200 t/s)
        - gpt-oss-120b: openai/gpt-oss-120b (500 t/s)
        - gpt-oss-20b: openai/gpt-oss-20b (1000 t/s)
        - whisper: whisper-large-v3
        - whisper-turbo: whisper-large-v3-turbo
    """

    MODEL_MAP = {
        # Production models only
        "llama-8b": "llama-3.1-8b-instant",
        "llama-70b": "llama-3.3-70b-versatile",
        "llama-guard": "meta-llama/llama-guard-4-12b",
        "gpt-oss-120b": "openai/gpt-oss-120b",
        "gpt-oss-20b": "openai/gpt-oss-20b",
        # Whisper (audio transcription)
        "whisper": "whisper-large-v3",
        "whisper-turbo": "whisper-large-v3-turbo",
    }

    # Pricing per 1K tokens (from https://console.groq.com/docs/models)
    MODEL_PRICING = {
        "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
        "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
        "meta-llama/llama-guard-4-12b": {"input": 0.00020, "output": 0.00020},
        "openai/gpt-oss-120b": {"input": 0.00015, "output": 0.00060},
        "openai/gpt-oss-20b": {"input": 0.000075, "output": 0.00030},
    }

    # Whisper pricing per hour (for reference)
    # whisper-large-v3: $0.111/hr, whisper-large-v3-turbo: $0.04/hr
    # Normalized to "tokens" for cost tracking (1 token = $0.01)
    WHISPER_TOKENS_PER_HOUR = {
        "whisper-large-v3": 11.1,
        "whisper-large-v3-turbo": 4.0,
    }

    def __init__(self, config: dict):
        # Auto-set pricing based on model before calling super().__init__
        model_alias = config.get("model", "llama-70b")
        model_id = self.MODEL_MAP.get(model_alias, model_alias)
        default_pricing = {"input": 0.00015, "output": 0.00060}  # gpt-oss-120b as fallback
        pricing = self.MODEL_PRICING.get(model_id, default_pricing)
        config.setdefault("cost_per_1k", pricing)

        super().__init__(config)
        self.client = Groq(api_key=self.api_key)
        self.max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt")

    def _get_api_key_from_env(self) -> str:
        return os.environ.get("GROQ_API_KEY", "")

    def _resolve_model_id(self) -> str:
        """Convert model alias to actual model ID."""
        return self.MODEL_MAP.get(self.model, self.model)

    def _call_api(self, messages: list[dict]) -> tuple[str, TokenUsage]:
        """Make API call to Groq and return (content, tokens)."""
        try:
            api_messages = messages.copy()
            if self.system_prompt:
                api_messages = [{"role": "system", "content": self.system_prompt}] + api_messages

            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=api_messages,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content or ""
            tokens = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )
            return content, tokens

        except GroqRateLimitError as e:
            raise RateLimitError(str(e))

    def transcribe(
        self,
        audio_file,
        model: str = "whisper-large-v3",
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> dict:
        """Transcribe audio to text using Whisper.

        Args:
            audio_file: File-like object (opened in binary mode)
            model: Whisper model to use
            language: Optional language code (e.g., "en")
            prompt: Optional prompt to guide transcription

        Returns:
            dict with text, language, duration, tokens
        """
        kwargs = {"file": audio_file, "model": model}
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        response = self.client.audio.transcriptions.create(**kwargs)

        duration_seconds = getattr(response, "duration", 0) or 0
        duration_hours = duration_seconds / 3600
        tokens_per_hour = self.WHISPER_TOKENS_PER_HOUR.get(model, 11.1)
        # Ensure at least 1 token for any transcription (fixes short audio returning 0)
        tokens = max(1, int(duration_hours * tokens_per_hour))

        return {
            "text": response.text,
            "language": getattr(response, "language", None),
            "duration": duration_seconds,
            "tokens": tokens,
        }
