"""Unit tests for white-label models and repositories.

These tests run against PostgreSQL using a per-test schema.
They test the repository layer with the production database backend.

Run with: pytest tests/unit/test_whitelabel.py -v
"""

import pytest
from datetime import datetime
from uuid import uuid4

# Skip all tests if sqlmodel is not installed
pytest.importorskip("sqlmodel")

from sqlmodel import Session, SQLModel

from runner.db.models import (
    User, UserCreate,
    Workspace, WorkspaceCreate,
    WhitelabelConfig, WhitelabelConfigCreate,
    WhitelabelAsset, WhitelabelAssetCreate,
    AssetType, DomainVerificationStatus,
)
from runner.content.repository import UserRepository
from runner.content.workspace_repository import WorkspaceRepository
from runner.content.whitelabel_repository import (
    WhitelabelConfigRepository,
    WhitelabelAssetRepository,
)
from tests.db_utils import create_test_engine, drop_test_schema, requires_db

pytestmark = requires_db  # Skip all tests in this module if DB not available


@pytest.fixture
def engine():
    """Create a PostgreSQL engine for testing."""
    engine, schema_name, database_url = create_test_engine()
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    drop_test_schema(database_url, schema_name)


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


# =============================================================================
# WhitelabelConfig Model Tests
# =============================================================================


class TestWhitelabelConfigModel:
    """Tests for WhitelabelConfig model."""

    def test_generate_verification_token(self):
        """Test verification token generation."""
        token = WhitelabelConfig.generate_verification_token()

        assert token.startswith("postmatiq-verify-")
        assert len(token) > 20

    def test_generate_dkim_selector(self):
        """Test DKIM selector generation."""
        selector = WhitelabelConfig.generate_dkim_selector()

        assert selector.startswith("pm")
        assert len(selector) == 10  # "pm" + 8 hex chars


# =============================================================================
# WhitelabelConfigRepository Tests
# =============================================================================


class TestWhitelabelConfigRepository:
    """Tests for WhitelabelConfigRepository."""

    def test_create_config(self, session, test_workspace):
        """Test creating a white-label configuration."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            custom_domain="app.example.com",
            primary_color="#1a73e8",
        ))

        assert config.id is not None
        assert config.workspace_id == test_workspace.id
        assert config.custom_domain == "app.example.com"
        assert config.primary_color == "#1a73e8"
        assert config.domain_verified is False
        assert config.is_active is True
        assert config.created_at is not None

    def test_get_config(self, session, test_workspace):
        """Test getting a configuration by ID."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            company_name="Acme Corp",
        ))

        fetched = repo.get(config.id)

        assert fetched is not None
        assert fetched.id == config.id
        assert fetched.company_name == "Acme Corp"

    def test_get_config_not_found(self, session):
        """Test getting a non-existent configuration."""
        repo = WhitelabelConfigRepository(session)
        config = repo.get(uuid4())

        assert config is None

    def test_get_by_workspace(self, session, test_workspace):
        """Test getting configuration by workspace."""
        repo = WhitelabelConfigRepository(session)
        repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            company_name="Test Company",
        ))

        config = repo.get_by_workspace(test_workspace.id)

        assert config is not None
        assert config.company_name == "Test Company"

    def test_get_by_domain(self, session, test_workspace):
        """Test getting configuration by custom domain."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            custom_domain="app.example.com",
        ))
        # Verify the domain
        repo.verify_domain(config.id)

        fetched = repo.get_by_domain("app.example.com")

        assert fetched is not None
        assert fetched.id == config.id

    def test_get_by_domain_unverified(self, session, test_workspace):
        """Test that unverified domains are not returned."""
        repo = WhitelabelConfigRepository(session)
        repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            custom_domain="unverified.example.com",
        ))

        config = repo.get_by_domain("unverified.example.com")

        assert config is None

    def test_get_by_domain_inactive(self, session, test_workspace):
        """Test that inactive domains are not returned."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            custom_domain="inactive.example.com",
        ))
        repo.verify_domain(config.id)
        repo.deactivate(config.id)

        fetched = repo.get_by_domain("inactive.example.com")

        assert fetched is None

    def test_list_verified_domains(self, session, test_user):
        """Test listing verified domains."""
        repo = WhitelabelConfigRepository(session)
        ws_repo = WorkspaceRepository(session)

        # Create multiple workspaces with configs
        ws1 = ws_repo.create(WorkspaceCreate(name="WS1", slug="ws1", owner_id=test_user.id))
        ws2 = ws_repo.create(WorkspaceCreate(name="WS2", slug="ws2", owner_id=test_user.id))
        ws3 = ws_repo.create(WorkspaceCreate(name="WS3", slug="ws3", owner_id=test_user.id))

        config1 = repo.create(WhitelabelConfigCreate(
            workspace_id=ws1.id, custom_domain="verified1.com"
        ))
        config2 = repo.create(WhitelabelConfigCreate(
            workspace_id=ws2.id, custom_domain="verified2.com"
        ))
        repo.create(WhitelabelConfigCreate(
            workspace_id=ws3.id, custom_domain="unverified.com"
        ))

        # Verify only first two
        repo.verify_domain(config1.id)
        repo.verify_domain(config2.id)

        verified = repo.list_verified_domains()

        assert len(verified) == 2
        domains = {c.custom_domain for c in verified}
        assert domains == {"verified1.com", "verified2.com"}

    def test_update_config(self, session, test_workspace):
        """Test updating configuration fields."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            primary_color="#000000",
        ))

        updated = repo.update(
            config.id,
            primary_color="#ffffff",
            secondary_color="#cccccc",
        )

        assert updated is not None
        assert updated.primary_color == "#ffffff"
        assert updated.secondary_color == "#cccccc"
        assert updated.updated_at is not None

    def test_verify_domain(self, session, test_workspace):
        """Test verifying a domain."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            custom_domain="verify.example.com",
        ))

        verified = repo.verify_domain(config.id)

        assert verified is not None
        assert verified.domain_verified is True
        assert verified.domain_verification_status == DomainVerificationStatus.VERIFIED.value
        assert verified.domain_verified_at is not None

    def test_verify_email_domain(self, session, test_workspace):
        """Test verifying an email domain."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
            email_domain="mail.example.com",
        ))

        verified = repo.verify_email_domain(config.id)

        assert verified is not None
        assert verified.email_domain_verified is True

    def test_deactivate_and_activate(self, session, test_workspace):
        """Test deactivating and activating a configuration."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
        ))

        # Deactivate
        deactivated = repo.deactivate(config.id)
        assert deactivated.is_active is False

        # Activate
        activated = repo.activate(config.id)
        assert activated.is_active is True

    def test_delete_config(self, session, test_workspace):
        """Test deleting a configuration."""
        repo = WhitelabelConfigRepository(session)
        config = repo.create(WhitelabelConfigCreate(
            workspace_id=test_workspace.id,
        ))

        result = repo.delete(config.id)

        assert result is True
        assert repo.get(config.id) is None

    def test_delete_config_not_found(self, session):
        """Test deleting a non-existent configuration."""
        repo = WhitelabelConfigRepository(session)
        result = repo.delete(uuid4())

        assert result is False


# =============================================================================
# WhitelabelAssetRepository Tests
# =============================================================================


class TestWhitelabelAssetRepository:
    """Tests for WhitelabelAssetRepository."""

    def test_create_asset(self, session, test_workspace):
        """Test creating a white-label asset."""
        repo = WhitelabelAssetRepository(session)
        asset = repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logos/logo.png",
        ))

        assert asset.id is not None
        assert asset.workspace_id == test_workspace.id
        assert asset.asset_type == AssetType.LOGO.value
        assert asset.file_path == "/uploads/logos/logo.png"
        assert asset.uploaded_at is not None

    def test_get_asset(self, session, test_workspace):
        """Test getting an asset by ID."""
        repo = WhitelabelAssetRepository(session)
        asset = repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.FAVICON.value,
            file_path="/uploads/favicons/favicon.ico",
        ))

        fetched = repo.get(asset.id)

        assert fetched is not None
        assert fetched.id == asset.id

    def test_get_asset_not_found(self, session):
        """Test getting a non-existent asset."""
        repo = WhitelabelAssetRepository(session)
        asset = repo.get(uuid4())

        assert asset is None

    def test_get_by_workspace_and_type(self, session, test_workspace):
        """Test getting asset by workspace and type."""
        repo = WhitelabelAssetRepository(session)

        # Create multiple assets of same type
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logos/old_logo.png",
        ))
        newer_asset = repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logos/new_logo.png",
        ))

        # Should return the most recent
        asset = repo.get_by_workspace_and_type(test_workspace.id, AssetType.LOGO)

        assert asset is not None
        assert asset.id == newer_asset.id

    def test_list_by_workspace(self, session, test_workspace):
        """Test listing all assets for a workspace."""
        repo = WhitelabelAssetRepository(session)
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logo.png",
        ))
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.FAVICON.value,
            file_path="/uploads/favicon.ico",
        ))

        assets = repo.list_by_workspace(test_workspace.id)

        assert len(assets) == 2

    def test_list_by_type(self, session, test_workspace):
        """Test listing assets by type."""
        repo = WhitelabelAssetRepository(session)
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logo1.png",
        ))
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logo2.png",
        ))
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.BANNER.value,
            file_path="/uploads/banner.png",
        ))

        logos = repo.list_by_type(test_workspace.id, AssetType.LOGO)

        assert len(logos) == 2

    def test_delete_asset(self, session, test_workspace):
        """Test deleting an asset."""
        repo = WhitelabelAssetRepository(session)
        asset = repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logo.png",
        ))

        result = repo.delete(asset.id)

        assert result is True
        assert repo.get(asset.id) is None

    def test_delete_asset_not_found(self, session):
        """Test deleting a non-existent asset."""
        repo = WhitelabelAssetRepository(session)
        result = repo.delete(uuid4())

        assert result is False

    def test_delete_by_workspace_and_type(self, session, test_workspace):
        """Test deleting all assets of a type for a workspace."""
        repo = WhitelabelAssetRepository(session)
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logo1.png",
        ))
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.LOGO.value,
            file_path="/uploads/logo2.png",
        ))
        repo.create(WhitelabelAssetCreate(
            workspace_id=test_workspace.id,
            asset_type=AssetType.FAVICON.value,
            file_path="/uploads/favicon.ico",
        ))

        count = repo.delete_by_workspace_and_type(test_workspace.id, AssetType.LOGO)

        assert count == 2
        assert len(repo.list_by_type(test_workspace.id, AssetType.LOGO)) == 0
        assert len(repo.list_by_type(test_workspace.id, AssetType.FAVICON)) == 1


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for white-label enums."""

    def test_asset_type_values(self):
        """Test AssetType enum values."""
        assert AssetType.LOGO.value == "logo"
        assert AssetType.FAVICON.value == "favicon"
        assert AssetType.BANNER.value == "banner"

    def test_domain_verification_status_values(self):
        """Test DomainVerificationStatus enum values."""
        assert DomainVerificationStatus.PENDING.value == "pending"
        assert DomainVerificationStatus.VERIFIED.value == "verified"
        assert DomainVerificationStatus.FAILED.value == "failed"
