"""Analytics models: AnalyticsImport, PostMetric, DailyMetric, etc."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# AnalyticsImport
# =============================================================================

class AnalyticsImportBase(SQLModel):
    """Base analytics import fields."""

    platform_name: str = Field(index=True)
    filename: str
    import_date: datetime = Field(default_factory=datetime.utcnow)
    row_count: Optional[int] = None
    status: str = Field(default="pending")
    error_message: Optional[str] = None
    import_type: Optional[str] = None


class AnalyticsImport(UUIDModel, AnalyticsImportBase, table=True):
    """AnalyticsImport table - track uploaded analytics files."""

    __tablename__ = "analytics_imports"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class AnalyticsImportCreate(AnalyticsImportBase):
    """Schema for creating a new analytics import."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# PostMetric
# =============================================================================

class PostMetricBase(SQLModel):
    """Base post metric fields."""

    platform_name: str = Field(index=True)
    external_url: Optional[str] = None
    post_date: Optional[date] = None
    impressions: Optional[int] = None
    engagement_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    clicks: Optional[int] = None
    metric_date: date = Field(index=True)
    # Delta columns for tracking changes
    impressions_delta: Optional[int] = None
    engagement_delta: Optional[int] = None
    likes_delta: Optional[int] = None
    comments_delta: Optional[int] = None
    shares_delta: Optional[int] = None
    clicks_delta: Optional[int] = None


class PostMetric(UUIDModel, PostMetricBase, TimestampMixin, table=True):
    """PostMetric table - normalized metrics from all platforms."""

    __tablename__ = "post_metrics"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    post_id: Optional[UUID] = Field(default=None, foreign_key="posts.id", index=True)
    import_id: Optional[UUID] = Field(default=None, foreign_key="analytics_imports.id")

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class PostMetricCreate(PostMetricBase):
    """Schema for creating a new post metric."""

    user_id: UUID
    post_id: Optional[UUID] = None
    import_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None


# =============================================================================
# DailyMetric
# =============================================================================

class DailyMetricBase(SQLModel):
    """Base daily metric fields."""

    platform_name: str
    metric_date: date = Field(index=True)
    impressions: Optional[int] = None
    engagements: Optional[int] = None


class DailyMetric(UUIDModel, DailyMetricBase, TimestampMixin, table=True):
    """DailyMetric table - daily aggregate metrics."""

    __tablename__ = "daily_metrics"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    import_id: Optional[UUID] = Field(default=None, foreign_key="analytics_imports.id")

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class DailyMetricCreate(DailyMetricBase):
    """Schema for creating a new daily metric."""

    user_id: UUID
    import_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None


# =============================================================================
# FollowerMetric
# =============================================================================

class FollowerMetricBase(SQLModel):
    """Base follower metric fields."""

    platform_name: str
    metric_date: date = Field(index=True)
    new_followers: Optional[int] = None
    total_followers: Optional[int] = None


class FollowerMetric(UUIDModel, FollowerMetricBase, TimestampMixin, table=True):
    """FollowerMetric table - daily follower data."""

    __tablename__ = "follower_metrics"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    import_id: Optional[UUID] = Field(default=None, foreign_key="analytics_imports.id")

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class FollowerMetricCreate(FollowerMetricBase):
    """Schema for creating a new follower metric."""

    user_id: UUID
    import_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None


# =============================================================================
# AudienceDemographic
# =============================================================================

class AudienceDemographicBase(SQLModel):
    """Base audience demographic fields."""

    platform_name: str
    category: str  # e.g., "job_title", "location", "industry"
    value: str
    percentage: Optional[float] = None
    metric_date: Optional[date] = None


class AudienceDemographic(UUIDModel, AudienceDemographicBase, TimestampMixin, table=True):
    """AudienceDemographic table - overall audience demographics."""

    __tablename__ = "audience_demographics"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    import_id: Optional[UUID] = Field(default=None, foreign_key="analytics_imports.id")

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class AudienceDemographicCreate(AudienceDemographicBase):
    """Schema for creating a new audience demographic."""

    user_id: UUID
    import_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None


# =============================================================================
# PostDemographic
# =============================================================================

class PostDemographicBase(SQLModel):
    """Base post demographic fields."""

    platform_name: str
    external_url: str = Field(index=True)
    category: str
    value: str
    percentage: Optional[float] = None


class PostDemographic(UUIDModel, PostDemographicBase, TimestampMixin, table=True):
    """PostDemographic table - per-post demographics."""

    __tablename__ = "post_demographics"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    import_id: Optional[UUID] = Field(default=None, foreign_key="analytics_imports.id")

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class PostDemographicCreate(PostDemographicBase):
    """Schema for creating a new post demographic."""

    user_id: UUID
    import_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None
