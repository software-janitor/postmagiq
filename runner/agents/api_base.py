"""Base class for SDK-based API agents."""

import os
import time
from abc import abstractmethod
from typing import Optional

from runner.agents.base import BaseAgent
from runner.models import AgentResult, TokenUsage


class APIAgent(BaseAgent):
    """Base class for agents that use official SDK APIs.

    Unlike CLIAgent which uses subprocess invocation, APIAgent uses
    the official Python SDKs (anthropic, openai, google-generativeai)
    for direct API calls. This provides:
    - Better error handling and retry logic
    - Proper rate limit handling with exponential backoff
    - In-memory session management via message history
    - More accurate token tracking from API responses
    """

    # Retry settings for rate limit errors
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2  # seconds
    RETRY_BACKOFF_MAX = 60  # max backoff seconds

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key") or self._get_api_key_from_env()
        self.model = config.get("model")
        self.model_id = self._resolve_model_id()
        self.messages: list[dict] = []  # Conversation history for sessions
        self.timeout = config.get("timeout", 300)

        if not self.api_key:
            raise ValueError(
                f"API key required for {self.name}. "
                f"Set via config or environment variable."
            )

    @abstractmethod
    def _get_api_key_from_env(self) -> str:
        """Get API key from environment variable."""
        pass

    @abstractmethod
    def _resolve_model_id(self) -> str:
        """Convert model alias to actual model ID."""
        pass

    @abstractmethod
    def _call_api(self, messages: list[dict]) -> tuple[str, TokenUsage]:
        """Make API call and return (content, tokens).

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Tuple of (response content string, TokenUsage)

        Raises:
            RateLimitError: When rate limited (will be retried)
            Exception: Other API errors
        """
        pass

    def invoke(self, prompt: str, input_files: Optional[list[str]] = None) -> AgentResult:
        """One-shot invocation (no history)."""
        full_prompt = self._build_prompt(prompt, input_files)
        messages = [{"role": "user", "content": full_prompt}]
        return self._execute(messages)

    def invoke_with_session(
        self, session_id: str, prompt: str, input_files: Optional[list[str]] = None
    ) -> AgentResult:
        """Invocation with conversation history.

        Unlike CLI agents that use native session IDs, API agents
        maintain session context via an in-memory messages list.
        """
        full_prompt = self._build_prompt(prompt, input_files)
        self.messages.append({"role": "user", "content": full_prompt})
        result = self._execute(self.messages)
        if result.success:
            self.messages.append({"role": "assistant", "content": result.content})
        return result

    def _build_prompt(self, prompt: str, input_files: Optional[list[str]] = None) -> str:
        """Build full prompt including file contents if provided."""
        if not input_files:
            return prompt

        file_contents = []
        for path in input_files:
            if os.path.exists(path):
                with open(path) as f:
                    content = f.read()
                file_contents.append(f"## File: {path}\n\n{content}")

        if file_contents:
            return prompt + "\n\n" + "\n\n".join(file_contents)
        return prompt

    def _execute(self, messages: list[dict]) -> AgentResult:
        """Execute API call with error handling and retries."""
        start_time = time.time()
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                content, tokens = self._call_api(messages)
                duration = time.time() - start_time

                return AgentResult(
                    success=True,
                    content=content,
                    tokens=tokens,
                    duration_s=duration,
                    session_id=None,  # API agents don't have native sessions
                    cost_usd=self.calculate_cost(tokens),
                )

            except RateLimitError as e:
                last_error = str(e)
                if attempt < self.MAX_RETRIES:
                    backoff = min(
                        self.RETRY_BACKOFF_BASE * (2 ** attempt),
                        self.RETRY_BACKOFF_MAX
                    )
                    print(
                        f"[{self.name}] Rate limited, waiting {backoff}s "
                        f"before retry {attempt + 2}/{self.MAX_RETRIES + 1}..."
                    )
                    time.sleep(backoff)

            except Exception as e:
                duration = time.time() - start_time
                return AgentResult(
                    success=False,
                    content="",
                    tokens=TokenUsage(input_tokens=0, output_tokens=0),
                    duration_s=duration,
                    error=str(e),
                )

        # All retries exhausted
        return AgentResult(
            success=False,
            content="",
            tokens=TokenUsage(input_tokens=0, output_tokens=0),
            duration_s=time.time() - start_time,
            error=last_error or "Rate limit retries exhausted",
        )

    def extract_tokens(self, raw_response: str) -> TokenUsage:
        """Extract token counts from raw response.

        For API agents, tokens are tracked directly from API responses,
        so this method is not typically used.
        """
        return TokenUsage(input_tokens=0, output_tokens=0)

    def supports_native_session(self) -> bool:
        """API agents don't have native CLI sessions."""
        return False

    @property
    def session_type(self) -> str:
        """Session type is 'memory' - we manage history in Python."""
        return "memory"

    def clear_session(self) -> None:
        """Clear conversation history."""
        self.messages = []


class RateLimitError(Exception):
    """Raised when API returns a rate limit error."""
    pass
