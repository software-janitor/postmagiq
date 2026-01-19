"""Platform model for content streams (LinkedIn, Threads, etc.)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


class PlatformBase(SQLModel):
    """Base platform fields shared across Create/Read/Update."""

    name: str = Field(index=True)
    description: Optional[str] = None
    post_format: Optional[str] = None
    default_word_count: Optional[int] = None
    uses_enemies: bool = Field(default=True)
    is_active: bool = Field(default=True)


class Platform(UUIDModel, PlatformBase, TimestampMixin, table=True):
    """Platform table - content stream definitions.

    Each platform defines the format and rules for content
    published to that destination (LinkedIn, Threads, blog, etc.).
    """

    __tablename__ = "platforms"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class PlatformCreate(PlatformBase):
    """Schema for creating a new platform."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


class PlatformRead(PlatformBase):
    """Schema for reading platform data."""

    id: UUID
    user_id: UUID
    workspace_id: Optional[UUID]
    created_at: datetime
