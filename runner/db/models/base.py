"""Base models for SQLModel tables.

All tables use UUID primary keys for security (anti-ID guessing) and
scalability (distributed systems friendly).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UUIDModel(SQLModel):
    """Base model with UUID primary key.

    All tables should inherit from this to ensure consistent
    primary key handling across the system.
    """

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )


class TimestampMixin(SQLModel):
    """Mixin for created_at and updated_at timestamps.

    Use with UUIDModel:
        class User(UUIDModel, TimestampMixin, table=True):
            name: str
    """

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )
