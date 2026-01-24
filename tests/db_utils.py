"""PostgreSQL test database helpers."""

import os
import uuid

from sqlalchemy import text
from sqlmodel import create_engine

from runner.config import DATABASE_URL as DEFAULT_DATABASE_URL


def _database_url() -> str:
    """Resolve the database URL for tests."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_test_engine():
    """Create a PostgreSQL engine bound to a unique schema."""
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
