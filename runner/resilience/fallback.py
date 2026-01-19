"""Fallback chain for model and service failures.

Provides automatic fallback to alternative models/services when
the primary fails. Useful for:
- Model unavailability
- Rate limiting
- Cost optimization

Usage:
    chain = FallbackChain([
        ("claude-opus", opus_agent),
        ("claude-sonnet", sonnet_agent),
        ("gpt-4o", gpt4_agent),
    ])

    result = await chain.invoke(prompt)
    print(f"Used model: {result.model_used}")
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

from runner.resilience.retry import RetryPolicy, with_retry

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class FallbackResult:
    """Result from fallback chain execution."""
    success: bool
    result: Any
    model_used: str
    attempts: list[dict] = field(default_factory=list)
    warning: Optional[str] = None

    @property
    def degraded(self) -> bool:
        """Whether a fallback model was used."""
        return len(self.attempts) > 1


class FallbackChain:
    """Chain of fallback models/services.

    Tries models in order until one succeeds. Each model can have
    its own retry policy.

    Usage:
        chain = FallbackChain([
            ("claude-opus", opus_agent),
            ("claude-sonnet", sonnet_agent),
            ("gpt-4o", gpt4_agent),
        ])

        result = await chain.invoke(prompt)

        if result.degraded:
            logger.warning(f"Used fallback: {result.model_used}")
    """

    def __init__(
        self,
        models: list[tuple[str, Any]],
        retry_policy: Optional[RetryPolicy] = None,
        on_fallback: Optional[Callable[[str, str, Exception], None]] = None,
    ):
        """Initialize fallback chain.

        Args:
            models: List of (name, agent) tuples in priority order
            retry_policy: Retry policy for each model attempt
            on_fallback: Callback when falling back (from_model, to_model, error)
        """
        if not models:
            raise ValueError("At least one model required")

        self.models = models
        self.retry_policy = retry_policy or RetryPolicy(max_retries=1)
        self.on_fallback = on_fallback

    async def invoke(
        self,
        prompt: str,
        **kwargs,
    ) -> FallbackResult:
        """Invoke the chain, trying models in order.

        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments passed to agents

        Returns:
            FallbackResult with the result and metadata
        """
        attempts = []
        last_error: Optional[Exception] = None

        for i, (model_name, agent) in enumerate(self.models):
            try:
                # Apply retry policy to each model
                result = await self._invoke_with_retry(
                    agent, prompt, model_name, **kwargs
                )

                attempts.append({
                    "model": model_name,
                    "success": True,
                })
                return FallbackResult(
                    success=True,
                    result=result,
                    model_used=model_name,
                    attempts=attempts,
                    warning=f"Used fallback model {model_name}" if i > 0 else None,
                )

            except Exception as e:
                last_error = e
                attempts.append({
                    "model": model_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "success": False,
                })

                logger.warning(f"Model {model_name} failed: {e}")

                # Call fallback callback if there's a next model
                if i < len(self.models) - 1 and self.on_fallback:
                    next_model = self.models[i + 1][0]
                    self.on_fallback(model_name, next_model, e)

        # All models failed
        return FallbackResult(
            success=False,
            result=None,
            model_used="none",
            attempts=attempts,
            warning=f"All models failed. Last error: {last_error}",
        )

    async def _invoke_with_retry(
        self,
        agent: Any,
        prompt: str,
        model_name: str,
        **kwargs,
    ) -> Any:
        """Invoke agent with retry policy."""
        last_error: Optional[Exception] = None

        async for attempt in self.retry_policy.attempts():
            try:
                # Call the agent's invoke method
                if hasattr(agent, "invoke"):
                    result = await agent.invoke(prompt, **kwargs)
                elif callable(agent):
                    result = await agent(prompt, **kwargs)
                else:
                    raise TypeError(f"Agent {model_name} is not callable")

                return result

            except Exception as e:
                last_error = e

                if not self.retry_policy.should_retry(e, attempt.number):
                    raise

                logger.debug(
                    f"Retry {attempt.number + 1} for {model_name}: {e}"
                )
                await attempt.wait(e)

        if last_error:
            raise last_error


# Pre-configured fallback chains
def create_claude_fallback_chain(
    opus_agent: Any,
    sonnet_agent: Any,
    haiku_agent: Optional[Any] = None,
) -> FallbackChain:
    """Create a fallback chain for Claude models.

    Opus -> Sonnet -> Haiku
    """
    models = [
        ("claude-opus", opus_agent),
        ("claude-sonnet", sonnet_agent),
    ]
    if haiku_agent:
        models.append(("claude-haiku", haiku_agent))

    return FallbackChain(models)


def create_multi_provider_fallback_chain(
    claude_agent: Any,
    openai_agent: Any,
    gemini_agent: Optional[Any] = None,
) -> FallbackChain:
    """Create a fallback chain across providers.

    Claude -> OpenAI -> Gemini
    """
    models = [
        ("claude", claude_agent),
        ("openai", openai_agent),
    ]
    if gemini_agent:
        models.append(("gemini", gemini_agent))

    return FallbackChain(
        models,
        retry_policy=RetryPolicy(max_retries=2),
    )
