"""Market intelligence models for audience understanding and voice calibration.

These models support the market upgrade plan:
- Embeddings for semantic search (pgvector)
- Audience segments for targeting
- Calibrated voices for voice + audience fusion
- Niche vocabulary for domain-specific language
- Research sources for LLM-generated insights
- Content moderation for safety
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Column, JSON, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, Relationship, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin
from runner.db.custom_types import JsonOrArray, JsonOrVector


# =============================================================================
# Enums
# =============================================================================

class EmbeddingSourceType(str, Enum):
    VOICE_SAMPLE = "voice_sample"
    CONTENT = "content"
    RESEARCH = "research"
    VOCABULARY = "vocabulary"
    GUIDELINE = "guideline"


class ResearchSourceType(str, Enum):
    LLM_NICHE = "llm_niche"
    LLM_COMPETITOR = "llm_competitor"
    USER_PROVIDED = "user_provided"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    ARCHIVED = "archived"


class ModerationStatus(str, Enum):
    PASSED = "passed"
    FLAGGED = "flagged"
    BLOCKED = "blocked"


class ModerationType(str, Enum):
    POLICY = "policy"
    FACTUALITY = "factuality"
    PLAGIARISM = "plagiarism"
    BRAND_SAFETY = "brand_safety"


# =============================================================================
# Embedding Model (pgvector)
# =============================================================================

class Embedding(UUIDModel, table=True):
    """Embedding table for semantic search."""
    __tablename__ = "embeddings"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    source_type: str = Field(max_length=50)
    source_id: UUID
    embedding: list[float] = Field(
        sa_column=Column(JsonOrVector(1536), nullable=False)
    )
    chunk_text: str
    chunk_index: int = Field(default=0)
    # "metadata" is reserved on SQLAlchemy models, so map via metadata_json.
    metadata_json: Optional[dict] = Field(
        default=None,
        sa_column=Column("metadata", JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingCreate(BaseModel):
    """Schema for creating an embedding."""
    workspace_id: UUID
    source_type: str
    source_id: UUID
    chunk_text: str
    chunk_index: int = 0
    embedding: list[float]
    metadata: Optional[dict] = None


# =============================================================================
# Audience Segment Model
# =============================================================================

class AudienceSegment(UUIDModel, TimestampMixin, table=True):
    """Audience segment table."""
    __tablename__ = "audience_segments"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    name: str = Field(max_length=255)
    description: Optional[str] = None
    # profile stored as JSON: demographics, psychographics, language_profile, visual_preferences
    profile: dict = Field(sa_column=Column(JSON, nullable=False))
    confidence_score: Optional[Decimal] = Field(default=None, max_digits=3, decimal_places=2)
    is_primary: bool = Field(default=False)
    is_validated: bool = Field(default=False)

    # Relationships
    calibrated_voices: list["CalibratedVoice"] = Relationship(back_populates="segment")


class AudienceSegmentCreate(BaseModel):
    """Schema for creating an audience segment."""
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    profile: dict
    confidence_score: Optional[float] = None
    is_primary: bool = False
    is_validated: bool = False


class AudienceSegmentRead(BaseModel):
    """Schema for reading audience segment data."""
    id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str]
    profile: dict
    confidence_score: Optional[float]
    is_primary: bool
    is_validated: bool
    created_at: datetime
    updated_at: Optional[datetime]


# =============================================================================
# Calibrated Voice Model
# =============================================================================

class CalibratedVoice(UUIDModel, TimestampMixin, table=True):
    """Calibrated voice table - voice + audience fusion."""
    __tablename__ = "calibrated_voices"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    voice_profile_id: UUID = Field(foreign_key="voice_profiles.id")
    segment_id: UUID = Field(foreign_key="audience_segments.id")
    platform: str = Field(max_length=50)
    # voice_spec stored as JSON: preservation, adaptations, synthesis_rules, examples, anti_patterns
    voice_spec: dict = Field(sa_column=Column(JSON, nullable=False))
    usage_count: int = Field(default=0)
    avg_engagement_score: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=2)

    # Relationships
    segment: Optional[AudienceSegment] = Relationship(back_populates="calibrated_voices")


class CalibratedVoiceCreate(BaseModel):
    """Schema for creating a calibrated voice."""
    workspace_id: UUID
    voice_profile_id: UUID
    segment_id: UUID
    platform: str
    voice_spec: dict
    usage_count: int = 0
    avg_engagement_score: Optional[float] = None


class CalibratedVoiceRead(BaseModel):
    """Schema for reading calibrated voice data."""
    id: UUID
    workspace_id: UUID
    voice_profile_id: UUID
    segment_id: UUID
    platform: str
    voice_spec: dict
    usage_count: int
    avg_engagement_score: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]


# =============================================================================
# Niche Vocabulary Model
# =============================================================================

class NicheVocabulary(UUIDModel, table=True):
    """Niche vocabulary table."""
    __tablename__ = "niche_vocabulary"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    term: str = Field(max_length=255)
    definition: Optional[str] = None
    usage_examples: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(JsonOrArray(Text()), nullable=True),
    )
    segment_ids: Optional[list[UUID]] = Field(
        default=None,
        sa_column=Column(JsonOrArray(postgresql.UUID(as_uuid=True)), nullable=True),
    )
    sentiment: Optional[str] = Field(default=None, max_length=20)
    formality_level: Optional[Decimal] = Field(default=None, max_digits=3, decimal_places=2)
    source: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NicheVocabularyCreate(BaseModel):
    """Schema for creating niche vocabulary."""
    workspace_id: UUID
    term: str
    definition: Optional[str] = None
    usage_examples: Optional[list[str]] = None
    segment_ids: Optional[list[UUID]] = None
    sentiment: Optional[str] = None
    formality_level: Optional[float] = None
    source: Optional[str] = None


class NicheVocabularyRead(BaseModel):
    """Schema for reading niche vocabulary data."""
    id: UUID
    workspace_id: UUID
    term: str
    definition: Optional[str]
    usage_examples: Optional[list[str]]
    segment_ids: Optional[list[UUID]]
    sentiment: Optional[str]
    formality_level: Optional[float]
    source: Optional[str]
    created_at: datetime


# =============================================================================
# Research Source Model
# =============================================================================

class ResearchSource(UUIDModel, table=True):
    """Research source table - LLM-generated insights."""
    __tablename__ = "research_sources"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    source_type: str = Field(max_length=50)
    source_identifier: str = Field(max_length=255)
    raw_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    processed_insights: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class ResearchSourceCreate(BaseModel):
    """Schema for creating a research source."""
    workspace_id: UUID
    source_type: str
    source_identifier: str
    raw_data: Optional[dict] = None
    processed_insights: Optional[dict] = None
    collected_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class ResearchSourceRead(BaseModel):
    """Schema for reading research source data."""
    id: UUID
    workspace_id: UUID
    source_type: str
    source_identifier: str
    raw_data: Optional[dict]
    processed_insights: Optional[dict]
    collected_at: datetime
    processed_at: Optional[datetime]
    expires_at: Optional[datetime]


# =============================================================================
# Generated Content Model
# =============================================================================

class GeneratedContent(UUIDModel, TimestampMixin, table=True):
    """Generated content table."""
    __tablename__ = "generated_content"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    post_id: Optional[UUID] = Field(default=None, foreign_key="posts.id")
    content_type: str = Field(max_length=50)
    platform: str = Field(max_length=50)
    text_content: Optional[str] = None
    image_urls: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(JsonOrArray(Text()), nullable=True),
    )
    calibrated_voice_id: Optional[UUID] = Field(default=None, foreign_key="calibrated_voices.id")
    segment_id: Optional[UUID] = Field(default=None, foreign_key="audience_segments.id")
    generation_prompts: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    status: str = Field(default="draft", max_length=50)
    engagement_metrics: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    moderation_result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    posted_at: Optional[datetime] = None
    post_url: Optional[str] = None


class GeneratedContentCreate(BaseModel):
    """Schema for creating generated content."""
    workspace_id: UUID
    post_id: Optional[UUID] = None
    content_type: str
    calibrated_voice_id: Optional[UUID] = None
    segment_id: Optional[UUID] = None
    platform: str
    text_content: Optional[str] = None
    image_urls: Optional[list[str]] = None
    generation_prompts: Optional[dict] = None
    status: str = "draft"
    engagement_metrics: Optional[dict] = None
    moderation_result: Optional[dict] = None
    posted_at: Optional[datetime] = None
    post_url: Optional[str] = None


class GeneratedContentRead(BaseModel):
    """Schema for reading generated content data."""
    id: UUID
    workspace_id: UUID
    post_id: Optional[UUID]
    content_type: str
    calibrated_voice_id: Optional[UUID]
    segment_id: Optional[UUID]
    platform: str
    text_content: Optional[str]
    image_urls: Optional[list[str]]
    generation_prompts: Optional[dict]
    status: str
    engagement_metrics: Optional[dict]
    moderation_result: Optional[dict]
    posted_at: Optional[datetime]
    post_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


# =============================================================================
# Content Moderation Model
# =============================================================================

class ContentModeration(UUIDModel, table=True):
    """Content moderation table - safety checks."""
    __tablename__ = "content_moderation"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    content_id: UUID = Field(foreign_key="generated_content.id", index=True)
    content_type: str = Field(max_length=50)
    moderation_type: str = Field(max_length=50)
    status: str = Field(max_length=20)
    confidence: Optional[Decimal] = Field(default=None, max_digits=3, decimal_places=2)
    flags: Optional[list[str]] = Field(
        default=None,
        sa_column=Column(JsonOrArray(Text()), nullable=True),
    )
    details: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    reviewed_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentModerationCreate(BaseModel):
    """Schema for creating content moderation."""
    workspace_id: UUID
    content_id: UUID
    content_type: str
    moderation_type: str
    status: str
    confidence: Optional[float] = None
    flags: Optional[list[str]] = None
    details: Optional[dict] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None


class ContentModerationRead(BaseModel):
    """Schema for reading content moderation data."""
    id: UUID
    workspace_id: UUID
    content_id: UUID
    content_type: str
    moderation_type: str
    status: str
    confidence: Optional[float]
    flags: Optional[list[str]]
    details: Optional[dict]
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime
