"""Voice models: WritingSample, VoiceProfile."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# WritingSample
# =============================================================================

class WritingSampleBase(SQLModel):
    """Base writing sample fields."""

    source_type: str
    prompt_id: Optional[str] = None
    prompt_text: Optional[str] = None
    title: Optional[str] = None
    content: str
    word_count: Optional[int] = None


class WritingSample(UUIDModel, WritingSampleBase, TimestampMixin, table=True):
    """WritingSample table - raw stories for voice learning."""

    __tablename__ = "writing_samples"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class WritingSampleCreate(WritingSampleBase):
    """Schema for creating a new writing sample."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


class WritingSampleRead(WritingSampleBase):
    """Schema for reading writing sample data."""

    id: UUID
    user_id: UUID
    workspace_id: Optional[UUID]
    created_at: datetime


# =============================================================================
# VoiceProfile
# =============================================================================

class VoiceProfileBase(SQLModel):
    """Base voice profile fields."""

    name: str  # e.g., "Matthew Garcia", "Professional", "Conversational"
    slug: str  # unique identifier like "matthew-garcia"
    description: Optional[str] = None
    is_preset: bool = Field(default=False)  # True for system presets
    tone_description: Optional[str] = None  # how the voice sounds
    signature_phrases: Optional[str] = None  # phrases to use sparingly
    word_choices: Optional[str] = None  # preferred word choices
    example_excerpts: Optional[str] = None  # writing samples
    avoid_patterns: Optional[str] = None  # anti-patterns to avoid


class VoiceProfile(UUIDModel, VoiceProfileBase, TimestampMixin, table=True):
    """VoiceProfile table - voice templates for content generation."""

    __tablename__ = "voice_profiles"

    # Multi-tenancy: workspace_id is nullable for legacy/system presets
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )

    # Unique constraint on slug within workspace (including null workspace for presets)
    __table_args__ = (
        {"extend_existing": True},
    )


class VoiceProfileCreate(VoiceProfileBase):
    """Schema for creating a new voice profile."""

    workspace_id: Optional[UUID] = None


class VoiceProfileRead(VoiceProfileBase):
    """Schema for reading voice profile data."""

    id: UUID
    workspace_id: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]
