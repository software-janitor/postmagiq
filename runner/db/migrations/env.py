"""Alembic environment configuration for SQLModel migrations."""

from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Add the project root to the path so we can import runner modules
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

# Import all models to ensure they're registered with SQLModel metadata
from runner.db.models import (  # noqa: F401
    # Multi-tenancy
    Workspace,
    WorkspaceMembership,
    # Core
    User,
    Platform,
    Goal,
    Chapter,
    Post,
    # Session
    ActiveSession,
    # Voice
    WritingSample,
    VoiceProfile,
    # Workflow
    WorkflowRun,
    WorkflowOutput,
    WorkflowSession,
    WorkflowStateMetric,
    WorkflowPersona,
    # Image
    ImagePrompt,
    ImageConfigSet,
    ImageScene,
    ImagePose,
    ImageOutfit,
    ImageProp,
    ImageCharacter,
    # Character
    CharacterTemplate,
    OutfitPart,
    Outfit,
    OutfitItem,
    Character,
    CharacterOutfit,
    Sentiment,
    SceneCharacter,
    PropCategory,
    ScenePropRule,
    ContextPropRule,
    # Analytics
    AnalyticsImport,
    PostMetric,
    DailyMetric,
    FollowerMetric,
    AudienceDemographic,
    PostDemographic,
    # History
    RunRecord,
    InvocationRecord,
    AuditScoreRecord,
    PostIterationRecord,
)

from runner.config import DATABASE_URL

# Alembic Config object
config = context.config

# Override sqlalchemy.url from environment variable
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
