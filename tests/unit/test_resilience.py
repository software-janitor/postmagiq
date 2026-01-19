"""Tests for resilience utilities."""

import asyncio

from runner.resilience.fallback import FallbackChain
from runner.resilience.rate_limit import RateLimiter


class FailingAgent:
    async def invoke(self, prompt: str, **kwargs):
        raise RuntimeError("boom")


class SuccessfulAgent:
    async def invoke(self, prompt: str, **kwargs):
        return f"ok:{prompt}"


def test_rate_limiter_acquire_context_manager():
    limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=1000)

    async def run():
        async with limiter.acquire(tokens=5) as wait:
            assert wait >= 0.0

    asyncio.run(run())


def test_fallback_chain_marks_degraded_on_fallback():
    chain = FallbackChain([
        ("fail", FailingAgent()),
        ("ok", SuccessfulAgent()),
    ])

    result = asyncio.run(chain.invoke("hello"))

    assert result.success is True
    assert result.model_used == "ok"
    assert result.degraded is True
    assert result.attempts[-1]["success"] is True


def test_fallback_chain_not_degraded_on_first_success():
    chain = FallbackChain([
        ("ok", SuccessfulAgent()),
    ])

    result = asyncio.run(chain.invoke("hello"))

    assert result.success is True
    assert result.model_used == "ok"
    assert result.degraded is False
    assert result.attempts == [{"model": "ok", "success": True}]
