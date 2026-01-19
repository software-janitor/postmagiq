"""Rate limiting for external APIs.

Implements token bucket rate limiting to prevent hitting
API rate limits and getting blocked.

Usage:
    limiter = RateLimiter(
        requests_per_minute=60,
        tokens_per_minute=100000,
    )

    async with limiter.acquire(tokens=1500):
        result = await api.generate(prompt)
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        requests_per_minute: Max requests per minute (RPM)
        tokens_per_minute: Max tokens per minute (TPM)
        requests_per_day: Max requests per day (RPD)
        tokens_per_day: Max tokens per day (TPD)
    """
    requests_per_minute: Optional[int] = None
    tokens_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    tokens_per_day: Optional[int] = None


# Default rate limits per API
API_RATE_LIMITS = {
    "anthropic": RateLimitConfig(
        requests_per_minute=60,
        tokens_per_minute=100000,
    ),
    "openai": RateLimitConfig(
        requests_per_minute=500,
        tokens_per_minute=150000,
    ),
    "google": RateLimitConfig(
        requests_per_minute=60,
        tokens_per_minute=120000,
    ),
}


class TokenBucket:
    """Token bucket rate limiter.

    Allows bursting up to bucket capacity, then enforces rate limit.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.

        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Time in seconds waited for tokens
        """
        async with self._lock:
            wait_time = 0.0
            while True:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return wait_time

                # Calculate wait time for enough tokens
                tokens_needed = tokens - self.tokens
                wait = tokens_needed / self.refill_rate

                logger.debug(f"Rate limited: waiting {wait:.2f}s for {tokens} tokens")
                await asyncio.sleep(wait)
                wait_time += wait

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        refill = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + refill)
        self.last_refill = now


class RateLimiter:
    """Rate limiter for API calls.

    Combines request-based and token-based rate limiting.

    Usage:
        limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=100000,
        )

        async with limiter.acquire(tokens=1500):
            result = await api.generate(prompt)
    """

    def __init__(
        self,
        requests_per_minute: Optional[int] = None,
        tokens_per_minute: Optional[int] = None,
        requests_per_day: Optional[int] = None,
        tokens_per_day: Optional[int] = None,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute
            tokens_per_minute: Max tokens per minute
            requests_per_day: Max requests per day
            tokens_per_day: Max tokens per day
        """
        self._buckets: dict[str, TokenBucket] = {}

        # Request rate limiting (per minute)
        if requests_per_minute:
            self._buckets["rpm"] = TokenBucket(
                capacity=requests_per_minute,
                refill_rate=requests_per_minute / 60.0,
            )

        # Token rate limiting (per minute)
        if tokens_per_minute:
            self._buckets["tpm"] = TokenBucket(
                capacity=tokens_per_minute,
                refill_rate=tokens_per_minute / 60.0,
            )

        # Daily limits (slower refill)
        if requests_per_day:
            self._buckets["rpd"] = TokenBucket(
                capacity=requests_per_day,
                refill_rate=requests_per_day / 86400.0,
            )

        if tokens_per_day:
            self._buckets["tpd"] = TokenBucket(
                capacity=tokens_per_day,
                refill_rate=tokens_per_day / 86400.0,
            )

    def acquire(self, tokens: int = 1):
        """Acquire rate limit tokens.

        Args:
            tokens: Number of tokens for this request

        Returns:
            Async context manager
        """
        return _RateLimitContext(self, tokens)

    async def _acquire(self, tokens: int) -> float:
        """Internal acquire implementation."""
        total_wait = 0.0

        # Acquire from request bucket
        if "rpm" in self._buckets:
            wait = await self._buckets["rpm"].acquire(1)
            total_wait = max(total_wait, wait)

        if "rpd" in self._buckets:
            wait = await self._buckets["rpd"].acquire(1)
            total_wait = max(total_wait, wait)

        # Acquire from token buckets
        if tokens > 0:
            if "tpm" in self._buckets:
                wait = await self._buckets["tpm"].acquire(tokens)
                total_wait = max(total_wait, wait)

            if "tpd" in self._buckets:
                wait = await self._buckets["tpd"].acquire(tokens)
                total_wait = max(total_wait, wait)

        if total_wait > 0:
            logger.info(f"Rate limited for {total_wait:.2f}s")

        return total_wait

    @classmethod
    def for_api(cls, api_name: str) -> "RateLimiter":
        """Create a rate limiter with default limits for an API.

        Args:
            api_name: Name of the API (anthropic, openai, google)

        Returns:
            RateLimiter configured for the API
        """
        config = API_RATE_LIMITS.get(api_name, RateLimitConfig())
        return cls(
            requests_per_minute=config.requests_per_minute,
            tokens_per_minute=config.tokens_per_minute,
            requests_per_day=config.requests_per_day,
            tokens_per_day=config.tokens_per_day,
        )


class _RateLimitContext:
    """Async context manager for rate limiting."""

    def __init__(self, limiter: RateLimiter, tokens: int):
        self.limiter = limiter
        self.tokens = tokens

    async def __aenter__(self) -> float:
        return await self.limiter._acquire(self.tokens)

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
