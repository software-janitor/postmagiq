"""Resilience module for error handling and retry strategies.

This module provides:
- Retry policies with exponential backoff
- Circuit breakers for failing services
- Fallback model chains
- Rate limiting handling
- Cost controls and budget enforcement

Usage:
    from runner.resilience import RetryPolicy, with_retry

    policy = RetryPolicy(max_retries=3, backoff_base=1.0)

    @with_retry(policy)
    async def call_api():
        return await api.generate(...)

    # Or with the agent wrapper
    from runner.resilience import ResilientAgent

    agent = ResilientAgent(
        primary_agent=claude_agent,
        fallback_agents=[sonnet_agent, gpt4_agent],
        retry_policy=policy,
    )
    result = await agent.invoke(prompt)
"""

from runner.resilience.retry import (
    RetryPolicy,
    RetryableError,
    with_retry,
)
from runner.resilience.fallback import (
    FallbackChain,
    FallbackResult,
)
from runner.resilience.rate_limit import (
    RateLimiter,
    RateLimitConfig,
)
from runner.resilience.budget import (
    BudgetEnforcer,
    BudgetConfig,
    BudgetExceededError,
)

__all__ = [
    "RetryPolicy",
    "RetryableError",
    "with_retry",
    "FallbackChain",
    "FallbackResult",
    "RateLimiter",
    "RateLimitConfig",
    "BudgetEnforcer",
    "BudgetConfig",
    "BudgetExceededError",
]
