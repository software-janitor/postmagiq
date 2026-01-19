"""Database infrastructure for SQLModel + PostgreSQL.

This module provides the database engine, session management, and
utilities for the multi-tenancy foundation.

Usage:
    from runner.db import get_session, engine

    with get_session() as session:
        user = session.get(User, user_id)
"""

from runner.db.engine import engine, get_session, init_db

__all__ = [
    "engine",
    "get_session",
    "init_db",
]
