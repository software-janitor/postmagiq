"""PostgreSQL test database helpers."""

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import create_engine

from runner.config import DATABASE_URL as DEFAULT_DATABASE_URL


def _database_url() -> str:
    """Resolve the database URL for tests."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def is_database_available() -> bool:
    """Check if the database is available for tests."""
    try:
        database_url = _database_url()
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except (OperationalError, Exception):
        return False


# Pytest marker to skip tests when database is not available
requires_db = pytest.mark.skipif(
    not is_database_available(),
    reason="Database not available"
)


def create_test_engine():
    """Create a PostgreSQL engine bound to a unique schema.

    Raises OperationalError if database is not available.
    """
    database_url = _database_url()
    schema_name = f"test_{uuid.uuid4().hex}"

    admin_engine = create_engine(database_url, pool_pre_ping=True)
    with admin_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin_engine.dispose()

    test_engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={schema_name}"},
    )
    return test_engine, schema_name, database_url


def drop_test_schema(database_url: str, schema_name: str) -> None:
    """Drop a test schema and all dependent objects."""
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    with admin_engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
    admin_engine.dispose()


def get_test_engine():
    """Get engine for schema validation tests (uses main schema, read-only).

    Returns None if database is not available.
    """
    if not is_database_available():
        return None
    database_url = _database_url()
    return create_engine(database_url, pool_pre_ping=True)


# Decorator to skip test class if database is not available
skip_if_no_db = pytest.mark.skipif(
    not is_database_available(),
    reason="Database not available"
)
