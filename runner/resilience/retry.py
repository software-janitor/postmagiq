"""Retry policies with exponential backoff.

Provides configurable retry behavior for transient failures.

Usage:
    policy = RetryPolicy(max_retries=3, backoff_base=1.0)

    @with_retry(policy)
    async def call_api():
        return await api.generate(...)

    # Or manual retry
    async for attempt in policy.attempts():
        try:
            result = await call_api()
            break
        except RetryableError as e:
            if not attempt.should_retry:
                raise
            await attempt.wait()
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""

    def __init__(
        self, message: str, retriable: bool = True, retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.retriable = retriable
        self.retry_after = retry_after  # Hint from server (e.g., rate limit)


# Common retryable errors
RETRYABLE_EXCEPTIONS: tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    RetryableError,
)


@dataclass
class RetryPolicy:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default 3)
        backoff_base: Base delay in seconds (default 1.0)
        backoff_factor: Multiplier for exponential backoff (default 2.0)
        backoff_max: Maximum delay in seconds (default 60.0)
        jitter: Add random jitter to delays (default True)
        retryable_exceptions: Exception types to retry on
    """

    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_factor: float = 2.0
    backoff_max: float = 60.0
    jitter: bool = True
    retryable_exceptions: tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number (0-indexed)."""
        delay = self.backoff_base * (self.backoff_factor**attempt)
        delay = min(delay, self.backoff_max)

        if self.jitter:
            # Add up to 25% jitter
            delay = delay * (0.75 + random.random() * 0.5)

        return delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if we should retry for this exception."""
        if attempt >= self.max_retries:
            return False

        # Check if exception is retryable
        if isinstance(exception, RetryableError):
            return exception.retriable

        return isinstance(exception, self.retryable_exceptions)

    async def attempts(self):
        """Async generator for retry attempts.

        Usage:
            async for attempt in policy.attempts():
                try:
                    result = await call_api()
                    break
                except Exception as e:
                    if not attempt.should_retry:
                        raise
                    await attempt.wait()
        """
        for i in range(self.max_retries + 1):
            yield RetryAttempt(
                number=i,
                policy=self,
                is_last=i >= self.max_retries,
            )


@dataclass
class RetryAttempt:
    """Represents a single retry attempt."""

    number: int
    policy: RetryPolicy
    is_last: bool
    last_error: Optional[Exception] = None

    @property
    def should_retry(self) -> bool:
        """Whether we should retry after this attempt."""
        return not self.is_last

    async def wait(self, error: Optional[Exception] = None) -> None:
        """Wait before the next retry attempt."""
        if error:
            self.last_error = error

        # Check for retry_after hint from server
        if isinstance(error, RetryableError) and error.retry_after:
            delay = error.retry_after
        else:
            delay = self.policy.get_delay(self.number)

        logger.debug(f"Retry attempt {self.number + 1}, waiting {delay:.2f}s")
        await asyncio.sleep(delay)


def with_retry(
    policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """Decorator to add retry behavior to async functions.

    Args:
        policy: RetryPolicy to use (default: RetryPolicy())
        on_retry: Callback called on each retry with (exception, attempt_number)

    Usage:
        @with_retry(RetryPolicy(max_retries=3))
        async def call_api():
            return await api.generate(...)

        # With callback
        def log_retry(e, attempt):
            logger.warning(f"Retry {attempt}: {e}")

        @with_retry(on_retry=log_retry)
        async def call_api():
            ...
    """
    policy = policy or RetryPolicy()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error: Optional[Exception] = None

            async for attempt in policy.attempts():
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    if not policy.should_retry(e, attempt.number):
                        raise

                    if on_retry:
                        on_retry(e, attempt.number)

                    logger.warning(
                        f"Retry {attempt.number + 1}/{policy.max_retries}: {e}"
                    )
                    await attempt.wait(e)

            # Should never reach here, but just in case
            if last_error:
                raise last_error
            raise RuntimeError("Retry loop exited unexpectedly")

        return wrapper

    return decorator


# Pre-configured policies for common scenarios
DEFAULT_POLICY = RetryPolicy()

AGGRESSIVE_POLICY = RetryPolicy(
    max_retries=5,
    backoff_base=0.5,
    backoff_max=30.0,
)

CONSERVATIVE_POLICY = RetryPolicy(
    max_retries=2,
    backoff_base=2.0,
    backoff_max=120.0,
)

# For rate-limited APIs
RATE_LIMIT_POLICY = RetryPolicy(
    max_retries=5,
    backoff_base=10.0,
    backoff_factor=2.0,
    backoff_max=300.0,  # 5 minutes max
    jitter=True,
)
