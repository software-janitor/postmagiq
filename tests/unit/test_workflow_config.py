"""Unit tests for WorkflowConfig repository and API.

Tests for the dynamic workflow configuration system (Phase 11).
"""

import pytest
from datetime import datetime
from uuid import uuid4

# Skip all tests if sqlmodel is not installed
pytest.importorskip("sqlmodel")

from sqlmodel import Session, SQLModel

from runner.db.models import (
    WorkflowConfig,
    WorkflowConfigCreate,
    WorkflowConfigUpdate,
    WorkflowEnvironment,
)
from runner.content.workflow_config_repository import WorkflowConfigRepository
from tests.db_utils import create_test_engine, drop_test_schema


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
def sample_config_data():
    """Sample workflow config data for testing."""
    return WorkflowConfigCreate(
        name="Groq Production",
        slug="groq-production",
        description="Production workflow using Groq LLMs",
        environment=WorkflowEnvironment.production,
        features=["fast-inference", "whisper-transcription"],
        tier_required=None,
        enabled=True,
        is_default=False,
    )


@pytest.fixture
def test_config(session, sample_config_data):
    """Create a test workflow config."""
    repo = WorkflowConfigRepository(session)
    config = repo.create(sample_config_data)
    return config


# =============================================================================
# WorkflowConfigRepository Tests
# =============================================================================

class TestWorkflowConfigRepository:
    """Tests for WorkflowConfigRepository."""

    def test_create_config(self, session, sample_config_data):
        """Test creating a workflow config."""
        repo = WorkflowConfigRepository(session)
        config = repo.create(sample_config_data)

        assert config.id is not None
        assert config.name == "Groq Production"
        assert config.slug == "groq-production"
        assert config.environment == WorkflowEnvironment.production
        assert config.features == ["fast-inference", "whisper-transcription"]
        assert config.enabled is True
        assert config.is_default is False
        assert config.created_at is not None

    def test_get_by_id(self, session, test_config):
        """Test getting a config by ID."""
        repo = WorkflowConfigRepository(session)
        config = repo.get(test_config.id)

        assert config is not None
        assert config.id == test_config.id
        assert config.slug == test_config.slug

    def test_get_by_id_not_found(self, session):
        """Test getting a non-existent config."""
        repo = WorkflowConfigRepository(session)
        config = repo.get(uuid4())

        assert config is None

    def test_get_by_slug(self, session, test_config):
        """Test getting a config by slug."""
        repo = WorkflowConfigRepository(session)
        config = repo.get_by_slug("groq-production")

        assert config is not None
        assert config.id == test_config.id
        assert config.name == "Groq Production"

    def test_get_by_slug_not_found(self, session):
        """Test getting a non-existent config by slug."""
        repo = WorkflowConfigRepository(session)
        config = repo.get_by_slug("nonexistent")

        assert config is None

    def test_list_all(self, session):
        """Test listing all configs."""
        repo = WorkflowConfigRepository(session)

        # Create multiple configs
        repo.create(WorkflowConfigCreate(
            name="Config A", slug="config-a",
            environment=WorkflowEnvironment.production,
        ))
        repo.create(WorkflowConfigCreate(
            name="Config B", slug="config-b",
            environment=WorkflowEnvironment.development,
        ))

        configs = repo.list_all()
        assert len(configs) == 2
        # Should be ordered by name
        assert configs[0].name == "Config A"
        assert configs[1].name == "Config B"

    def test_list_enabled(self, session):
        """Test listing only enabled configs."""
        repo = WorkflowConfigRepository(session)

        repo.create(WorkflowConfigCreate(
            name="Enabled", slug="enabled",
            environment=WorkflowEnvironment.production,
            enabled=True,
        ))
        repo.create(WorkflowConfigCreate(
            name="Disabled", slug="disabled",
            environment=WorkflowEnvironment.production,
            enabled=False,
        ))

        configs = repo.list_enabled()
        assert len(configs) == 1
        assert configs[0].slug == "enabled"

    def test_list_by_environment(self, session):
        """Test listing configs by environment."""
        repo = WorkflowConfigRepository(session)

        repo.create(WorkflowConfigCreate(
            name="Prod Config", slug="prod",
            environment=WorkflowEnvironment.production,
        ))
        repo.create(WorkflowConfigCreate(
            name="Dev Config", slug="dev",
            environment=WorkflowEnvironment.development,
        ))

        prod_configs = repo.list_by_environment(WorkflowEnvironment.production)
        assert len(prod_configs) == 1
        assert prod_configs[0].slug == "prod"

        dev_configs = repo.list_by_environment(WorkflowEnvironment.development)
        assert len(dev_configs) == 1
        assert dev_configs[0].slug == "dev"

    def test_list_by_tier(self, session):
        """Test listing configs by tier."""
        repo = WorkflowConfigRepository(session)

        # No tier required - available to all
        repo.create(WorkflowConfigCreate(
            name="Free Config", slug="free",
            environment=WorkflowEnvironment.production,
            tier_required=None,
        ))
        # Requires pro tier
        repo.create(WorkflowConfigCreate(
            name="Pro Config", slug="pro",
            environment=WorkflowEnvironment.production,
            tier_required="pro",
        ))

        # Free tier should only see free config
        free_configs = repo.list_by_tier(None)
        assert len(free_configs) == 1
        assert free_configs[0].slug == "free"

        # Pro tier should see both
        pro_configs = repo.list_by_tier("pro")
        assert len(pro_configs) == 2

    def test_list_for_workspace(self, session):
        """Test listing configs for a workspace (environment + tier filter)."""
        repo = WorkflowConfigRepository(session)

        repo.create(WorkflowConfigCreate(
            name="Prod Free", slug="prod-free",
            environment=WorkflowEnvironment.production,
            tier_required=None,
        ))
        repo.create(WorkflowConfigCreate(
            name="Prod Pro", slug="prod-pro",
            environment=WorkflowEnvironment.production,
            tier_required="pro",
        ))
        repo.create(WorkflowConfigCreate(
            name="Dev Config", slug="dev",
            environment=WorkflowEnvironment.development,
        ))

        # Production + free tier
        configs = repo.list_for_workspace(WorkflowEnvironment.production, None)
        assert len(configs) == 1
        assert configs[0].slug == "prod-free"

        # Production + pro tier
        configs = repo.list_for_workspace(WorkflowEnvironment.production, "pro")
        assert len(configs) == 2

    def test_get_default(self, session):
        """Test getting the default config."""
        repo = WorkflowConfigRepository(session)

        repo.create(WorkflowConfigCreate(
            name="Not Default", slug="not-default",
            environment=WorkflowEnvironment.production,
            is_default=False,
        ))
        repo.create(WorkflowConfigCreate(
            name="Default", slug="default",
            environment=WorkflowEnvironment.production,
            is_default=True,
        ))

        default = repo.get_default()
        assert default is not None
        assert default.slug == "default"

    def test_get_default_none_set(self, session):
        """Test getting default when none is set."""
        repo = WorkflowConfigRepository(session)

        repo.create(WorkflowConfigCreate(
            name="Not Default", slug="not-default",
            environment=WorkflowEnvironment.production,
            is_default=False,
        ))

        default = repo.get_default()
        assert default is None

    def test_set_default(self, session):
        """Test setting a config as default (clears previous)."""
        repo = WorkflowConfigRepository(session)

        config1 = repo.create(WorkflowConfigCreate(
            name="Config 1", slug="config-1",
            environment=WorkflowEnvironment.production,
            is_default=True,
        ))
        config2 = repo.create(WorkflowConfigCreate(
            name="Config 2", slug="config-2",
            environment=WorkflowEnvironment.production,
            is_default=False,
        ))

        # Set config2 as default
        repo.set_default(config2.id)

        # Refresh from DB
        updated1 = repo.get(config1.id)
        updated2 = repo.get(config2.id)

        assert updated1.is_default is False
        assert updated2.is_default is True

    def test_update_config(self, session, test_config):
        """Test updating a config."""
        repo = WorkflowConfigRepository(session)

        update_data = WorkflowConfigUpdate(
            name="Updated Name",
            description="Updated description",
        )
        updated = repo.update(test_config.id, update_data)

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        # Unchanged fields should remain
        assert updated.slug == "groq-production"

    def test_enable_disable(self, session, test_config):
        """Test enabling and disabling a config."""
        repo = WorkflowConfigRepository(session)

        # Disable
        disabled = repo.disable(test_config.id)
        assert disabled.enabled is False

        # Enable
        enabled = repo.enable(test_config.id)
        assert enabled.enabled is True

    def test_delete_config(self, session, test_config):
        """Test deleting a config."""
        repo = WorkflowConfigRepository(session)

        deleted = repo.delete(test_config.id)
        assert deleted is True

        # Should not exist anymore
        config = repo.get(test_config.id)
        assert config is None

    def test_delete_config_not_found(self, session):
        """Test deleting a non-existent config."""
        repo = WorkflowConfigRepository(session)

        deleted = repo.delete(uuid4())
        assert deleted is False

    def test_upsert_create(self, session):
        """Test upserting a new config."""
        repo = WorkflowConfigRepository(session)

        data = WorkflowConfigCreate(
            name="New Config",
            slug="new-config",
            environment=WorkflowEnvironment.production,
        )
        config = repo.upsert("new-config", data)

        assert config.id is not None
        assert config.name == "New Config"

    def test_upsert_update(self, session, test_config):
        """Test upserting an existing config."""
        repo = WorkflowConfigRepository(session)

        data = WorkflowConfigCreate(
            name="Updated via Upsert",
            slug="groq-production",
            environment=WorkflowEnvironment.staging,
        )
        config = repo.upsert("groq-production", data)

        assert config.id == test_config.id
        assert config.name == "Updated via Upsert"
        assert config.environment == WorkflowEnvironment.staging
