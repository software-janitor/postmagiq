"""Groq API agent using the official Groq Python SDK."""

import os
from typing import Optional

from groq import Groq, RateLimitError as GroqRateLimitError

from runner.agents.api_base import APIAgent, RateLimitError
from runner.models import TokenUsage


class GroqAPIAgent(APIAgent):
    """Groq agent with chat completions and audio transcription.

    Model aliases:
        - llama-70b: llama-3.3-70b-versatile
        - llama-8b: llama-3.1-8b-instant
        - mixtral: mixtral-8x7b-32768
        - whisper: whisper-large-v3
    """

    MODEL_MAP = {
        # Llama 3.x
        "llama-70b": "llama-3.3-70b-versatile",
        "llama-8b": "llama-3.1-8b-instant",
        "llama-70b-specdec": "llama-3.3-70b-specdec",
        "llama-3.2-1b": "llama-3.2-1b-preview",
        "llama-3.2-3b": "llama-3.2-3b-preview",
        "llama-3.2-11b-vision": "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision": "llama-3.2-90b-vision-preview",
        # Llama 4
        "llama4-scout": "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama4-maverick": "meta-llama/llama-4-maverick-17b-128e-instruct",
        # Mixtral
        "mixtral": "mixtral-8x7b-32768",
        # Qwen
        "qwen-32b": "qwen/qwen3-32b",
        # Gemma
        "gemma2-9b": "gemma2-9b-it",
        # Whisper (audio transcription)
        "whisper": "whisper-large-v3",
        "whisper-turbo": "whisper-large-v3-turbo",
        "distil-whisper": "distil-whisper-large-v3-en",
    }

    MODEL_PRICING = {
        "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
        "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
        "llama-3.3-70b-specdec": {"input": 0.00059, "output": 0.00079},
        "llama-3.2-1b-preview": {"input": 0.00004, "output": 0.00004},
        "llama-3.2-3b-preview": {"input": 0.00006, "output": 0.00006},
        "llama-3.2-11b-vision-preview": {"input": 0.00018, "output": 0.00018},
        "llama-3.2-90b-vision-preview": {"input": 0.00090, "output": 0.00090},
        "meta-llama/llama-4-scout-17b-16e-instruct": {"input": 0.00011, "output": 0.00034},
        "meta-llama/llama-4-maverick-17b-128e-instruct": {"input": 0.00020, "output": 0.00060},
        "mixtral-8x7b-32768": {"input": 0.00024, "output": 0.00024},
        "qwen/qwen3-32b": {"input": 0.00029, "output": 0.00039},
        "gemma2-9b-it": {"input": 0.00020, "output": 0.00020},
    }

    # Whisper pricing normalized to tokens (1 token = $0.01)
    WHISPER_TOKENS_PER_HOUR = {
        "whisper-large-v3": 11.1,
        "whisper-large-v3-turbo": 4.0,
        "distil-whisper-large-v3-en": 2.0,
    }

    def __init__(self, config: dict):
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
