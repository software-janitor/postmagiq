"""Content models: Goal, Chapter, Post."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# Goal
# =============================================================================

class GoalBase(SQLModel):
    """Base goal fields shared across Create/Read/Update."""

    positioning: Optional[str] = None
    signature_thesis: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None
    onboarding_mode: Optional[str] = None
    onboarding_transcript: Optional[str] = None
    strategy_type: Optional[str] = None


class Goal(UUIDModel, GoalBase, TimestampMixin, table=True):
    """Goal table - user's content positioning goals per platform."""

    __tablename__ = "goals"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    platform_id: Optional[UUID] = Field(default=None, foreign_key="platforms.id", index=True)
    voice_profile_id: Optional[UUID] = Field(default=None, foreign_key="voice_profiles.id")
    image_config_set_id: Optional[UUID] = Field(default=None, foreign_key="image_config_sets.id")

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class GoalCreate(GoalBase):
    """Schema for creating a new goal."""

    user_id: UUID
    platform_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None


class GoalRead(GoalBase):
    """Schema for reading goal data."""

    id: UUID
    user_id: UUID
    platform_id: Optional[UUID]
    workspace_id: Optional[UUID]
    created_at: datetime


# =============================================================================
# Chapter
# =============================================================================

class ChapterBase(SQLModel):
    """Base chapter fields shared across Create/Read/Update."""

    chapter_number: int = Field(index=True)
    title: str
    description: Optional[str] = None
    theme: Optional[str] = None
    theme_description: Optional[str] = None
    weeks_start: Optional[int] = None
    weeks_end: Optional[int] = None


class Chapter(UUIDModel, ChapterBase, table=True):
    """Chapter table - content themes/sections per platform."""

    __tablename__ = "chapters"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    platform_id: Optional[UUID] = Field(default=None, foreign_key="platforms.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )

    # Unique constraint: one chapter number per user/platform
    __table_args__ = (
        # UniqueConstraint handled via unique_together in Alembic
    )


class ChapterCreate(ChapterBase):
    """Schema for creating a new chapter."""

    user_id: UUID
    platform_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None


class ChapterRead(ChapterBase):
    """Schema for reading chapter data."""

    id: UUID
    user_id: UUID
    platform_id: Optional[UUID]
    workspace_id: Optional[UUID]


# =============================================================================
# Post
# =============================================================================

class PostBase(SQLModel):
    """Base post fields shared across Create/Read/Update."""

    post_number: int = Field(index=True)
    topic: Optional[str] = None
    shape: Optional[str] = None
    cadence: Optional[str] = None
    entry_point: Optional[str] = None
    status: str = Field(default="not_started", index=True)
    story_used: Optional[str] = None
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    guidance: Optional[str] = None

    # Assignment fields (Phase 6)
    due_date: Optional[datetime] = None
    priority: Optional[str] = None  # low, medium, high, urgent
    estimated_hours: Optional[float] = None


class Post(UUIDModel, PostBase, table=True):
    """Post table - individual content pieces."""

    __tablename__ = "posts"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    chapter_id: UUID = Field(foreign_key="chapters.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )

    # Assignment: who is currently assigned to this post
    assignee_id: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        index=True,
    )


class PostCreate(PostBase):
    """Schema for creating a new post."""

    user_id: UUID
    chapter_id: UUID
    workspace_id: Optional[UUID] = None


class PostRead(PostBase):
    """Schema for reading post data."""

    id: UUID
    user_id: UUID
    chapter_id: UUID
    workspace_id: Optional[UUID]
