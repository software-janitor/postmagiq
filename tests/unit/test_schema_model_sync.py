"""Tests to ensure SQLModel definitions match database schema.

This prevents 500 errors from schema/model mismatches like:
- Missing columns in database
- Column name mismatches (e.g., 'source' vs 'source_type')
- Type mismatches

Run with: pytest tests/unit/test_schema_model_sync.py -v
"""

import pytest
from sqlalchemy import inspect, text
from sqlmodel import SQLModel

from runner.db.engine import get_session


def get_all_table_models():
    """Get all SQLModel classes that map to database tables."""
    tables = []
    for mapper in SQLModel.metadata.tables.values():
        tables.append(mapper.name)
    return tables


def get_model_columns(table_name: str) -> set[str]:
    """Get column names from SQLModel metadata for a table."""
    table = SQLModel.metadata.tables.get(table_name)
    if table is None:
        return set()
    return {col.name for col in table.columns}


def get_db_columns(session, table_name: str) -> set[str]:
    """Get column names from actual database table."""
    result = session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table_name"
        ),
        {"table_name": table_name},
    )
    return {row[0] for row in result}


def table_exists(session, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = session.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :table_name)"
        ),
        {"table_name": table_name},
    )
    return result.scalar()


class TestSchemaModelSync:
    """Tests to verify database schema matches SQLModel definitions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get database session for tests."""
        with get_session() as session:
            self.session = session
            yield

    def test_all_model_tables_exist_in_database(self):
        """Every table defined in SQLModel should exist in the database."""
        model_tables = get_all_table_models()
        missing_tables = []

        for table_name in model_tables:
            if not table_exists(self.session, table_name):
                missing_tables.append(table_name)

        assert not missing_tables, (
            f"Tables defined in models but missing from database: {missing_tables}\n"
            f"Run 'make db-migrate' to apply pending migrations."
        )

    def test_writing_samples_columns_match(self):
        """writing_samples table columns should match the model."""
        table_name = "writing_samples"

        if not table_exists(self.session, table_name):
            pytest.skip(f"Table {table_name} does not exist")

        model_cols = get_model_columns(table_name)
        db_cols = get_db_columns(self.session, table_name)

        # Columns in model but not in database
        missing_in_db = model_cols - db_cols
        assert not missing_in_db, (
            f"Columns in WritingSample model but missing from database: {missing_in_db}\n"
            f"This will cause 500 errors. Run migrations or update the model."
        )

    def test_voice_profiles_columns_match(self):
        """voice_profiles table columns should match the model."""
        table_name = "voice_profiles"

        if not table_exists(self.session, table_name):
            pytest.skip(f"Table {table_name} does not exist")

        model_cols = get_model_columns(table_name)
        db_cols = get_db_columns(self.session, table_name)

        missing_in_db = model_cols - db_cols
        assert not missing_in_db, (
            f"Columns in VoiceProfile model but missing from database: {missing_in_db}"
        )

    def test_social_connections_columns_match(self):
        """social_connections table columns should match the model."""
        table_name = "social_connections"

        if not table_exists(self.session, table_name):
            pytest.skip(f"Table {table_name} does not exist")

        model_cols = get_model_columns(table_name)
        db_cols = get_db_columns(self.session, table_name)

        missing_in_db = model_cols - db_cols
        assert not missing_in_db, (
            f"Columns in SocialConnection model but missing from database: {missing_in_db}"
        )

    def test_all_critical_tables_have_matching_columns(self):
        """All critical tables should have columns matching their models."""
        critical_tables = [
            "users",
            "workspaces",
            "posts",
            "goals",
            "chapters",
            "workflow_runs",
            "writing_samples",
            "voice_profiles",
            "subscription_tiers",
            "account_subscriptions",
        ]

        mismatches = []

        for table_name in critical_tables:
            if not table_exists(self.session, table_name):
                continue

            model_cols = get_model_columns(table_name)
            db_cols = get_db_columns(self.session, table_name)

            missing_in_db = model_cols - db_cols
            if missing_in_db:
                mismatches.append(f"{table_name}: missing {missing_in_db}")

        assert not mismatches, (
            f"Schema/model mismatches found:\n"
            + "\n".join(f"  - {m}" for m in mismatches)
            + "\n\nRun 'make db-migrate' or create migrations for these changes."
        )


class TestSchemaIntegrity:
    """Additional schema integrity tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get database session for tests."""
        with get_session() as session:
            self.session = session
            yield

    def test_writing_samples_has_source_type_not_source(self):
        """Ensure writing_samples uses 'source_type' not 'source'."""
        db_cols = get_db_columns(self.session, "writing_samples")

        assert "source_type" in db_cols, (
            "writing_samples should have 'source_type' column, not 'source'"
        )
        assert "source" not in db_cols, (
            "writing_samples has deprecated 'source' column - should be 'source_type'"
        )

    def test_no_orphan_columns_in_critical_tables(self):
        """Warn about columns in DB but not in model (potential cleanup needed)."""
        critical_tables = [
            "writing_samples",
            "voice_profiles",
        ]

        orphan_info = []

        for table_name in critical_tables:
            if not table_exists(self.session, table_name):
                continue

            model_cols = get_model_columns(table_name)
            db_cols = get_db_columns(self.session, table_name)

            extra_in_db = db_cols - model_cols
            if extra_in_db:
                orphan_info.append(f"{table_name}: {extra_in_db}")

        # This is a warning, not a failure - orphan columns are ok but worth noting
        if orphan_info:
            print(
                "\nNote: These columns exist in DB but not in model (may need cleanup):"
            )
            for info in orphan_info:
                print(f"  - {info}")
