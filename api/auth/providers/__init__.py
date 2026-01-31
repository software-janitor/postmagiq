"""Authentication provider factory.

Provides a pluggable authentication system. The provider is selected
via the AUTH_PROVIDER environment variable:

    AUTH_PROVIDER=local  (default) - Local JWT with password auth
    AUTH_PROVIDER=clerk  - Clerk external authentication

Usage:
    from api.auth.providers import get_provider

    provider = get_provider()
    result = await provider.verify_token(token)
"""

import os
from functools import lru_cache
from typing import TYPE_CHECKING

from api.auth.providers.base import AuthResult, BaseAuthProvider

if TYPE_CHECKING:
    pass

# Environment variable for provider selection
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "local")


@lru_cache(maxsize=1)
def get_provider() -> BaseAuthProvider:
    """Get the configured authentication provider.

    Returns a singleton instance of the auth provider based on
    the AUTH_PROVIDER environment variable.

    Note: The provider is cached. Use clear_provider_cache() to reset
    after changing AUTH_PROVIDER (mainly for testing).

    Returns:
        BaseAuthProvider: The configured auth provider instance

    Raises:
        ValueError: If AUTH_PROVIDER is set to an unknown value
    """
    # Read env var at call time, not import time
    provider_name = os.getenv("AUTH_PROVIDER", "local").lower()

    if provider_name == "local":
        from api.auth.providers.local import LocalAuthProvider

        return LocalAuthProvider()

    if provider_name == "clerk":
        from api.auth.providers.clerk import ClerkAuthProvider

        return ClerkAuthProvider()

    raise ValueError(
        f"Unknown AUTH_PROVIDER: {provider_name}. "
        f"Supported values: local, clerk"
    )


def clear_provider_cache() -> None:
    """Clear the cached provider instance.

    Useful for testing when switching providers.
    """
    get_provider.cache_clear()


__all__ = [
    "AuthResult",
    "BaseAuthProvider",
    "get_provider",
    "clear_provider_cache",
    "AUTH_PROVIDER",
]
