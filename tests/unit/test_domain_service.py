"""Unit tests for domain service.

Tests domain verification, DKIM generation, and custom domain middleware.
Uses mocked DNS lookups to avoid external dependencies.

Run with: pytest tests/unit/test_domain_service.py -v
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from uuid import uuid4

# Skip all tests if sqlmodel is not installed
pytest.importorskip("sqlmodel")

from sqlmodel import Session, SQLModel, create_engine, select

from runner.db.models import (
    User, UserCreate,
    Workspace, WorkspaceCreate,
    WhitelabelConfig,
    DomainVerificationStatus,
)
from runner.content.repository import UserRepository
from runner.content.workspace_repository import WorkspaceRepository
from api.services.domain_service import (
    DomainService,
    DomainNotFoundError,
    DomainAlreadyVerifiedError,
    DomainVerificationFailedError,
    DKIMGenerationError,
    get_workspace_by_custom_domain,
    VERIFICATION_TXT_PREFIX,
    DKIM_TXT_PREFIX,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a test session."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user(session):
    """Create a test user."""
    repo = UserRepository(session)
    user = repo.create(UserCreate(full_name="Test User", email="test@example.com"))
    return user


@pytest.fixture
def test_workspace(session, test_user):
    """Create a test workspace."""
    repo = WorkspaceRepository(session)
    workspace = repo.create(WorkspaceCreate(
        name="Test Workspace",
        slug="test-workspace",
        owner_id=test_user.id,
    ))
    return workspace


@pytest.fixture
def domain_service():
    """Create a domain service instance."""
    return DomainService()


# =============================================================================
# Domain Verification Token Tests
# =============================================================================


class TestGenerateVerificationToken:
    """Tests for generate_verification_token."""

    def test_generates_token_for_new_domain(self, session, test_workspace, domain_service):
        """Test generating a token for a new custom domain."""
        token = domain_service.generate_verification_token(
            session,
            test_workspace.id,
            "content.agency.com",
        )

        assert token is not None
        assert token.startswith("postmatiq-verify-")
        assert len(token) > 20

        # Verify config was created
        config = session.exec(
            select(WhitelabelConfig).where(WhitelabelConfig.workspace_id == test_workspace.id)
        ).first()

        assert config is not None
        assert config.custom_domain == "content.agency.com"
        assert config.domain_verification_token == token
        assert config.domain_verified is False
        assert config.domain_verification_status == DomainVerificationStatus.PENDING.value

    def test_updates_token_for_existing_config(self, session, test_workspace, domain_service):
        """Test generating a new token replaces the old one."""
        # Create initial config
        token1 = domain_service.generate_verification_token(
            session, test_workspace.id, "domain1.com"
        )

        # Generate new token for different domain
        token2 = domain_service.generate_verification_token(
            session, test_workspace.id, "domain2.com"
        )

        assert token1 != token2

        config = session.exec(
            select(WhitelabelConfig).where(WhitelabelConfig.workspace_id == test_workspace.id)
        ).first()

        assert config.custom_domain == "domain2.com"
        assert config.domain_verification_token == token2

    def test_rejects_already_verified_domain(self, session, test_workspace, domain_service):
        """Test error when trying to verify an already verified domain."""
        # Create and verify a domain
        config = WhitelabelConfig(
            workspace_id=test_workspace.id,
            custom_domain="verified.com",
            domain_verified=True,
            domain_verification_status=DomainVerificationStatus.VERIFIED.value,
        )
        session.add(config)
        session.commit()

        # Attempt to generate token for same domain should fail
        with pytest.raises(DomainAlreadyVerifiedError):
            domain_service.generate_verification_token(
                session, test_workspace.id, "verified.com"
            )


# =============================================================================
# Domain Verification Tests
# =============================================================================


class TestVerifyDomain:
    """Tests for verify_domain."""

    def test_verifies_domain_with_correct_txt_record(self, session, test_workspace, domain_service):
        """Test successful domain verification with correct DNS record."""
        # Setup domain with token
        token = domain_service.generate_verification_token(
            session, test_workspace.id, "test.agency.com"
        )

        # Mock DNS lookup to return the token
        mock_rdata = MagicMock()
        mock_rdata.__str__ = lambda x: f'"{token}"'

        with patch("api.services.domain_service.dns.resolver.resolve") as mock_resolve:
            mock_resolve.return_value = [mock_rdata]

            result = domain_service.verify_domain(session, test_workspace.id)

        assert result is True

        # Verify config was updated
        config = session.exec(
            select(WhitelabelConfig).where(WhitelabelConfig.workspace_id == test_workspace.id)
        ).first()

        assert config.domain_verified is True
        assert config.domain_verification_status == DomainVerificationStatus.VERIFIED.value
        assert config.domain_verified_at is not None

    def test_fails_with_wrong_txt_record(self, session, test_workspace, domain_service):
        """Test verification fails with incorrect DNS record."""
        # Setup domain with token
        domain_service.generate_verification_token(
            session, test_workspace.id, "test.agency.com"
        )

        # Mock DNS lookup to return wrong value
        mock_rdata = MagicMock()
        mock_rdata.__str__ = lambda x: '"wrong-token"'

        with patch("api.services.domain_service.dns.resolver.resolve") as mock_resolve:
            mock_resolve.return_value = [mock_rdata]

            with pytest.raises(DomainVerificationFailedError):
                domain_service.verify_domain(session, test_workspace.id)

        # Verify config was marked as failed
        config = session.exec(
            select(WhitelabelConfig).where(WhitelabelConfig.workspace_id == test_workspace.id)
        ).first()

        assert config.domain_verified is False
        assert config.domain_verification_status == DomainVerificationStatus.FAILED.value

    def test_fails_with_no_dns_record(self, session, test_workspace, domain_service):
        """Test verification fails when no DNS record exists."""
        # Setup domain with token
        domain_service.generate_verification_token(
            session, test_workspace.id, "test.agency.com"
        )

        # Mock DNS lookup to raise NXDOMAIN
        import dns.resolver
        with patch("api.services.domain_service.dns.resolver.resolve") as mock_resolve:
            mock_resolve.side_effect = dns.resolver.NXDOMAIN()

            with pytest.raises(DomainVerificationFailedError):
                domain_service.verify_domain(session, test_workspace.id)

    def test_fails_with_no_domain_configured(self, session, test_workspace, domain_service):
        """Test verification fails when no domain is configured."""
        with pytest.raises(DomainNotFoundError):
            domain_service.verify_domain(session, test_workspace.id)


# =============================================================================
# Domain Status Tests
# =============================================================================


class TestGetVerificationStatus:
    """Tests for get_verification_status."""

    def test_returns_not_configured_when_no_config(self, session, test_workspace, domain_service):
        """Test status when no config exists."""
        status = domain_service.get_verification_status(session, test_workspace.id)

        assert status["configured"] is False
        assert status["custom_domain"] is None
        assert status["verified"] is False

    def test_returns_pending_status_with_instructions(self, session, test_workspace, domain_service):
        """Test status for pending verification includes instructions."""
        domain_service.generate_verification_token(
            session, test_workspace.id, "pending.agency.com"
        )

        status = domain_service.get_verification_status(session, test_workspace.id)

        assert status["configured"] is True
        assert status["custom_domain"] == "pending.agency.com"
        assert status["verified"] is False
        assert status["status"] == DomainVerificationStatus.PENDING.value
        assert status["instructions"] is not None
        assert "txt_record_name" in status["instructions"]
        assert "_quillexir-verify.pending.agency.com" in status["instructions"]["txt_record_name"]

    def test_returns_verified_status(self, session, test_workspace, domain_service):
        """Test status for verified domain."""
        config = WhitelabelConfig(
            workspace_id=test_workspace.id,
            custom_domain="verified.agency.com",
            domain_verified=True,
            domain_verification_status=DomainVerificationStatus.VERIFIED.value,
            domain_verified_at=datetime.utcnow(),
        )
        session.add(config)
        session.commit()

        status = domain_service.get_verification_status(session, test_workspace.id)

        assert status["configured"] is True
        assert status["custom_domain"] == "verified.agency.com"
        assert status["verified"] is True
        assert status["verified_at"] is not None


# =============================================================================
# Remove Domain Tests
# =============================================================================


class TestRemoveCustomDomain:
    """Tests for remove_custom_domain."""

    def test_removes_configured_domain(self, session, test_workspace, domain_service):
        """Test removing a configured domain."""
        config = WhitelabelConfig(
            workspace_id=test_workspace.id,
            custom_domain="remove-me.com",
            domain_verified=True,
            domain_verification_token="some-token",
        )
        session.add(config)
        session.commit()

        result = domain_service.remove_custom_domain(session, test_workspace.id)

        assert result is True

        config = session.exec(
            select(WhitelabelConfig).where(WhitelabelConfig.workspace_id == test_workspace.id)
        ).first()

        assert config.custom_domain is None
        assert config.domain_verified is False
        assert config.domain_verification_token is None

    def test_returns_false_when_no_domain(self, session, test_workspace, domain_service):
        """Test returning false when no domain is configured."""
        result = domain_service.remove_custom_domain(session, test_workspace.id)
        assert result is False


# =============================================================================
# DKIM Generation Tests
# =============================================================================


class TestGenerateDKIMKeypair:
    """Tests for generate_dkim_keypair."""

    def test_generates_valid_keypair(self, session, test_workspace, domain_service):
        """Test generating a DKIM keypair."""
        result = domain_service.generate_dkim_keypair(
            session,
            test_workspace.id,
            "mail.agency.com",
        )

        assert "selector" in result
        assert result["selector"].startswith("pm")
        assert "email_domain" in result
        assert result["email_domain"] == "mail.agency.com"
        assert "dns_record_name" in result
        assert "dns_record_value" in result
        assert "v=DKIM1; k=rsa; p=" in result["dns_record_value"]
        assert "private_key" in result
        assert "-----BEGIN PRIVATE KEY-----" in result["private_key"]

        # Verify config was updated
        config = session.exec(
            select(WhitelabelConfig).where(WhitelabelConfig.workspace_id == test_workspace.id)
        ).first()

        assert config is not None
        assert config.email_domain == "mail.agency.com"
        assert config.dkim_selector is not None
        assert config.dkim_public_key is not None
        assert config.email_domain_verified is False

    def test_generates_correct_dns_record_name(self, session, test_workspace, domain_service):
        """Test DNS record name format."""
        result = domain_service.generate_dkim_keypair(
            session,
            test_workspace.id,
            "mail.agency.com",
        )

        # DNS record should be {selector}._domainkey.{domain}
        expected_pattern = f"{result['selector']}._domainkey.mail.agency.com"
        assert result["dns_record_name"] == expected_pattern


# =============================================================================
# DKIM Verification Tests
# =============================================================================


class TestVerifyDKIMSetup:
    """Tests for verify_dkim_setup."""

    def test_verifies_dkim_with_correct_record(self, session, test_workspace, domain_service):
        """Test successful DKIM verification."""
        # Generate DKIM keys first
        result = domain_service.generate_dkim_keypair(
            session, test_workspace.id, "mail.agency.com"
        )

        # Mock DNS lookup to return the public key
        mock_rdata = MagicMock()
        mock_rdata.__str__ = lambda x: f'"v=DKIM1; k=rsa; p={result["dns_record_value"].split("p=")[1]}"'

        with patch("api.services.domain_service.dns.resolver.resolve") as mock_resolve:
            mock_resolve.return_value = [mock_rdata]

            verified = domain_service.verify_dkim_setup(session, test_workspace.id)

        assert verified is True

        # Verify config was updated
        config = session.exec(
            select(WhitelabelConfig).where(WhitelabelConfig.workspace_id == test_workspace.id)
        ).first()

        assert config.email_domain_verified is True

    def test_fails_with_no_email_domain(self, session, test_workspace, domain_service):
        """Test verification fails when no email domain is configured."""
        with pytest.raises(DomainNotFoundError):
            domain_service.verify_dkim_setup(session, test_workspace.id)


# =============================================================================
# DKIM Status Tests
# =============================================================================


class TestGetDKIMStatus:
    """Tests for get_dkim_status."""

    def test_returns_not_configured_when_no_email_domain(self, session, test_workspace, domain_service):
        """Test status when no email domain is configured."""
        status = domain_service.get_dkim_status(session, test_workspace.id)

        assert status["configured"] is False
        assert status["email_domain"] is None
        assert status["selector"] is None
        assert status["verified"] is False

    def test_returns_configured_status_with_instructions(self, session, test_workspace, domain_service):
        """Test status includes instructions for pending verification."""
        domain_service.generate_dkim_keypair(
            session, test_workspace.id, "mail.agency.com"
        )

        status = domain_service.get_dkim_status(session, test_workspace.id)

        assert status["configured"] is True
        assert status["email_domain"] == "mail.agency.com"
        assert status["selector"] is not None
        assert status["verified"] is False
        assert status["instructions"] is not None
        assert status["instructions"]["type"] == "TXT"


# =============================================================================
# Custom Domain Lookup Tests
# =============================================================================


class TestGetWorkspaceByCustomDomain:
    """Tests for get_workspace_by_custom_domain utility function."""

    def test_returns_workspace_id_for_verified_domain(self, session, test_workspace):
        """Test finding workspace by verified custom domain."""
        config = WhitelabelConfig(
            workspace_id=test_workspace.id,
            custom_domain="active.agency.com",
            domain_verified=True,
            is_active=True,
        )
        session.add(config)
        session.commit()

        workspace_id = get_workspace_by_custom_domain(session, "active.agency.com")

        assert workspace_id == test_workspace.id

    def test_returns_none_for_unverified_domain(self, session, test_workspace):
        """Test returns None for unverified domain."""
        config = WhitelabelConfig(
            workspace_id=test_workspace.id,
            custom_domain="pending.agency.com",
            domain_verified=False,
            is_active=True,
        )
        session.add(config)
        session.commit()

        workspace_id = get_workspace_by_custom_domain(session, "pending.agency.com")

        assert workspace_id is None

    def test_returns_none_for_inactive_domain(self, session, test_workspace):
        """Test returns None for inactive configuration."""
        config = WhitelabelConfig(
            workspace_id=test_workspace.id,
            custom_domain="inactive.agency.com",
            domain_verified=True,
            is_active=False,
        )
        session.add(config)
        session.commit()

        workspace_id = get_workspace_by_custom_domain(session, "inactive.agency.com")

        assert workspace_id is None

    def test_returns_none_for_unknown_domain(self, session, test_workspace):
        """Test returns None for unknown domain."""
        workspace_id = get_workspace_by_custom_domain(session, "unknown.com")

        assert workspace_id is None


# =============================================================================
# Custom Domain Middleware Tests
# =============================================================================


class TestCustomDomainMiddleware:
    """Tests for CustomDomainMiddleware."""

    def test_passes_through_default_domains(self):
        """Test default domains are passed through without lookup."""
        from api.middleware.custom_domain import CustomDomainMiddleware

        middleware = CustomDomainMiddleware(app=None)

        assert middleware._is_default_domain("localhost") is True
        assert middleware._is_default_domain("app.quillexir.com") is True
        assert middleware._is_default_domain("api.quillexir.com") is True
        assert middleware._is_default_domain("quillexir.com") is True

    def test_identifies_custom_domains(self):
        """Test custom domains are identified correctly."""
        from api.middleware.custom_domain import CustomDomainMiddleware

        middleware = CustomDomainMiddleware(app=None)

        assert middleware._is_default_domain("custom.agency.com") is False
        assert middleware._is_default_domain("content.example.org") is False

    def test_extracts_host_without_port(self):
        """Test host extraction strips port number."""
        from api.middleware.custom_domain import CustomDomainMiddleware
        from unittest.mock import MagicMock

        middleware = CustomDomainMiddleware(app=None)

        request = MagicMock()
        request.headers.get.return_value = "custom.agency.com:8000"

        host = middleware._extract_host(request)

        assert host == "custom.agency.com"

    def test_handles_subdomains_of_default_domains(self):
        """Test subdomains of default domains are treated as default."""
        from api.middleware.custom_domain import CustomDomainMiddleware

        middleware = CustomDomainMiddleware(app=None)

        assert middleware._is_default_domain("staging.app.quillexir.com") is True
        assert middleware._is_default_domain("dev.quillexir.com") is True


# =============================================================================
# WhitelabelConfig Model Tests
# =============================================================================


class TestWhitelabelConfigModel:
    """Tests for WhitelabelConfig model helper methods."""

    def test_generate_verification_token_format(self):
        """Test verification token has correct format."""
        token = WhitelabelConfig.generate_verification_token()

        assert token.startswith("postmatiq-verify-")
        assert len(token) > 20

    def test_generate_verification_token_uniqueness(self):
        """Test each token is unique."""
        tokens = [WhitelabelConfig.generate_verification_token() for _ in range(10)]

        assert len(set(tokens)) == 10  # All unique

    def test_generate_dkim_selector_format(self):
        """Test DKIM selector has correct format."""
        selector = WhitelabelConfig.generate_dkim_selector()

        assert selector.startswith("pm")
        assert len(selector) == 10  # "pm" + 8 hex chars

    def test_generate_dkim_selector_uniqueness(self):
        """Test each selector is unique."""
        selectors = [WhitelabelConfig.generate_dkim_selector() for _ in range(10)]

        assert len(set(selectors)) == 10  # All unique
