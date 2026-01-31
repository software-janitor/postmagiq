"""Tests for authentication providers."""

import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

from api.auth.providers import get_provider, clear_provider_cache, AUTH_PROVIDER
from api.auth.providers.base import AuthResult, BaseAuthProvider
from api.auth.providers.local import LocalAuthProvider


class TestAuthResult:
    """Tests for AuthResult dataclass."""

    def test_valid_result(self):
        """AuthResult with valid=True includes user info."""
        result = AuthResult(
            valid=True,
            user_id="user_123",
            email="test@example.com",
            full_name="Test User",
            provider="clerk",
            raw_claims={"sub": "user_123"},
        )
        assert result.valid is True
        assert result.user_id == "user_123"
        assert result.email == "test@example.com"
        assert result.full_name == "Test User"
        assert result.provider == "clerk"
        assert result.error is None

    def test_invalid_result(self):
        """AuthResult with valid=False includes error."""
        result = AuthResult(
            valid=False,
            provider="local",
            error="Token expired",
        )
        assert result.valid is False
        assert result.user_id is None
        assert result.error == "Token expired"


class TestLocalAuthProvider:
    """Tests for LocalAuthProvider."""

    def test_name(self):
        """LocalAuthProvider has correct name."""
        provider = LocalAuthProvider()
        assert provider.name == "local"

    def test_supports_local_auth(self):
        """LocalAuthProvider supports local auth."""
        provider = LocalAuthProvider()
        assert provider.supports_local_auth is True

    @pytest.mark.asyncio
    async def test_verify_token_valid(self):
        """LocalAuthProvider verifies valid JWT."""
        from api.auth.jwt import create_access_token

        provider = LocalAuthProvider()
        user_id = str(uuid4())
        token = create_access_token({"sub": user_id})

        result = await provider.verify_token(token)

        assert result.valid is True
        assert result.user_id == user_id
        assert result.provider == "local"
        assert result.raw_claims is not None

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """LocalAuthProvider rejects invalid JWT."""
        provider = LocalAuthProvider()

        result = await provider.verify_token("invalid-token")

        assert result.valid is False
        assert result.provider == "local"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_verify_token_wrong_type(self):
        """LocalAuthProvider rejects non-access tokens."""
        from api.auth.jwt import create_refresh_token

        provider = LocalAuthProvider()
        token = create_refresh_token({"sub": str(uuid4())})

        result = await provider.verify_token(token)

        assert result.valid is False
        assert "token type" in result.error.lower()

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self):
        """LocalAuthProvider loads existing user."""
        provider = LocalAuthProvider()
        user_id = uuid4()

        # Mock the session and user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True

        mock_session = MagicMock()
        mock_session.get.return_value = mock_user

        auth_result = AuthResult(
            valid=True,
            user_id=str(user_id),
            provider="local",
        )

        user = await provider.get_or_create_user(auth_result, mock_session)

        assert user == mock_user
        mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_inactive(self):
        """LocalAuthProvider rejects inactive users."""
        provider = LocalAuthProvider()
        user_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = False

        mock_session = MagicMock()
        mock_session.get.return_value = mock_user

        auth_result = AuthResult(
            valid=True,
            user_id=str(user_id),
            provider="local",
        )

        user = await provider.get_or_create_user(auth_result, mock_session)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_or_create_user_invalid_result(self):
        """LocalAuthProvider returns None for invalid auth result."""
        provider = LocalAuthProvider()
        mock_session = MagicMock()

        auth_result = AuthResult(
            valid=False,
            provider="local",
            error="Invalid token",
        )

        user = await provider.get_or_create_user(auth_result, mock_session)

        assert user is None
        mock_session.get.assert_not_called()


class TestClerkAuthProvider:
    """Tests for ClerkAuthProvider."""

    def test_init_requires_jwks_url(self):
        """ClerkAuthProvider requires CLERK_JWKS_URL."""
        # Clear any existing value
        original = os.environ.get("CLERK_JWKS_URL")
        if "CLERK_JWKS_URL" in os.environ:
            del os.environ["CLERK_JWKS_URL"]

        try:
            # Reload the module to pick up the env change
            import importlib
            import api.auth.providers.clerk as clerk_module
            importlib.reload(clerk_module)

            with pytest.raises(RuntimeError) as exc_info:
                clerk_module.ClerkAuthProvider()
            assert "CLERK_JWKS_URL" in str(exc_info.value)
        finally:
            if original:
                os.environ["CLERK_JWKS_URL"] = original

    def test_name(self):
        """ClerkAuthProvider has correct name."""
        os.environ["CLERK_JWKS_URL"] = "https://test.clerk.dev/.well-known/jwks.json"
        try:
            import importlib
            import api.auth.providers.clerk as clerk_module
            importlib.reload(clerk_module)

            provider = clerk_module.ClerkAuthProvider()
            assert provider.name == "clerk"
        finally:
            del os.environ["CLERK_JWKS_URL"]

    def test_supports_local_auth(self):
        """ClerkAuthProvider does not support local auth."""
        os.environ["CLERK_JWKS_URL"] = "https://test.clerk.dev/.well-known/jwks.json"
        try:
            import importlib
            import api.auth.providers.clerk as clerk_module
            importlib.reload(clerk_module)

            provider = clerk_module.ClerkAuthProvider()
            assert provider.supports_local_auth is False
        finally:
            del os.environ["CLERK_JWKS_URL"]


class TestProviderFactory:
    """Tests for auth provider factory."""

    def setup_method(self):
        """Clear provider cache before each test."""
        clear_provider_cache()

    def test_default_is_local(self):
        """Default provider is local."""
        # Ensure AUTH_PROVIDER is not set to something else
        with patch.dict(os.environ, {"AUTH_PROVIDER": "local"}, clear=False):
            clear_provider_cache()
            provider = get_provider()
            assert isinstance(provider, LocalAuthProvider)

    def test_singleton_pattern(self):
        """Provider factory returns same instance."""
        with patch.dict(os.environ, {"AUTH_PROVIDER": "local"}, clear=False):
            clear_provider_cache()
            provider1 = get_provider()
            provider2 = get_provider()
            assert provider1 is provider2

    def test_cache_clear(self):
        """clear_provider_cache resets singleton."""
        with patch.dict(os.environ, {"AUTH_PROVIDER": "local"}, clear=False):
            clear_provider_cache()
            provider1 = get_provider()
            clear_provider_cache()
            provider2 = get_provider()
            # New instance after cache clear
            assert provider1 is not provider2

    def test_unknown_provider_raises(self):
        """Unknown provider raises ValueError."""
        with patch.dict(os.environ, {"AUTH_PROVIDER": "unknown"}, clear=False):
            clear_provider_cache()
            with pytest.raises(ValueError) as exc_info:
                get_provider()
            assert "unknown" in str(exc_info.value).lower()


class TestRequireLocalAuth:
    """Tests for require_local_auth dependency."""

    def test_local_provider_allows(self):
        """require_local_auth passes with local provider."""
        from api.routes.auth import require_local_auth

        with patch("api.routes.auth.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.supports_local_auth = True
            mock_get_provider.return_value = mock_provider

            # Should not raise
            require_local_auth()

    def test_external_provider_blocks(self):
        """require_local_auth raises with external provider."""
        from api.routes.auth import require_local_auth
        from fastapi import HTTPException

        with patch("api.routes.auth.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.supports_local_auth = False
            mock_provider.name = "clerk"
            mock_get_provider.return_value = mock_provider

            with pytest.raises(HTTPException) as exc_info:
                require_local_auth()

            assert exc_info.value.status_code == 400
            assert "clerk" in exc_info.value.detail.lower()
