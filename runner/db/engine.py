"""SQLModel engine and session management.

This module provides:
- Database engine creation with connection pooling
- Session factory for dependency injection
- Database initialization utilities

PostgreSQL is the primary database. SQLite support has been deprecated.
"""

from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from runner.config import DATABASE_URL

# Create engine with connection pooling
# pool_pre_ping ensures connections are valid before use
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session.

    Usage:
        with get_session() as session:
            user = session.get(User, user_id)
            session.add(new_post)
            session.commit()

    Yields:
        SQLModel Session instance
    """
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def get_session_dependency() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions.

    Usage in FastAPI:
        @app.get("/users/{user_id}")
        def get_user(user_id: UUID, session: Session = Depends(get_session_dependency)):
            return session.get(User, user_id)
    """
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Initialize database tables.

    Creates all tables defined in SQLModel models.
    Should only be used for development/testing.
    Use Alembic migrations for production.
    """
    # Import all models to ensure they're registered with SQLModel
    from runner.db.models import (  # noqa: F401
        User,
        Platform,
        Goal,
        Chapter,
        Post,
        Workspace,
        WorkspaceMembership,
        ActiveSession,
    )

    SQLModel.metadata.create_all(engine)


def drop_all_tables() -> None:
    """Drop all tables. USE WITH CAUTION - data loss will occur."""
    SQLModel.metadata.drop_all(engine)
