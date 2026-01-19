"""ID normalization helpers for SQLModel-backed services."""

from __future__ import annotations

from typing import Optional, Union
from uuid import UUID

from runner.content.repository import UserRepository
from runner.db.engine import get_session
from runner.db.models import UserCreate


SYSTEM_USER_EMAIL = "system@local"


def get_system_user_id() -> UUID:
    """Return the system user UUID, creating it if needed."""
    with get_session() as session:
        repo = UserRepository(session)
        user = repo.get_by_email(SYSTEM_USER_EMAIL)
        if not user:
            user = repo.create(UserCreate(full_name="System", email=SYSTEM_USER_EMAIL))
        return user.id


def normalize_user_id(user_id: Union[UUID, str, None]) -> Optional[UUID]:
    """Normalize user_id to UUID, creating system user when None."""
    if user_id is None:
        return get_system_user_id()
    if isinstance(user_id, UUID):
        return user_id
    if isinstance(user_id, str):
        try:
            return UUID(user_id)
        except ValueError:
            return None
    return None


def coerce_uuid(value: Union[UUID, str, None]) -> Optional[UUID]:
    """Convert a value to UUID if possible, returning None on failure."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None
