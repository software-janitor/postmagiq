"""Workspace model for multi-tenancy.

Workspaces are the boundary of data isolation. All content, analytics,
and workflow data belongs to a workspace. Users can belong to multiple
workspaces via WorkspaceMembership (see membership.py).
"""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON

from runner.db.models.base import UUIDModel, TimestampMixin


class WorkspaceBase(SQLModel):
    """Base workspace fields shared across Create/Read/Update."""

    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    description: Optional[str] = None


class Workspace(UUIDModel, WorkspaceBase, TimestampMixin, table=True):
    """Workspace table - the boundary of data isolation.

    Each workspace isolates content, analytics, and workflow data.
    Users access workspaces via memberships with specific roles.
    """

    __tablename__ = "workspaces"

    # Owner is the billing owner - there can only be one
    owner_id: UUID = Field(foreign_key="users.id", index=True)

    # Preferred workflow configuration (Phase 11 - Dynamic Workflow Config)
    # Nullable - if not set, uses system default from registry
    workflow_config_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workflow_configs.id",
        index=True,
    )

    # JSON settings for workspace-level configuration
    # Example: {"default_platform_id": "...", "features": {...}}
    # Note: Using JSON instead of JSONB for SQLite compatibility in tests.
    # PostgreSQL will still benefit from JSON indexing.
    settings: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a new workspace."""

    owner_id: UUID
    workflow_config_id: Optional[UUID] = None
    settings: Optional[dict[str, Any]] = None


class WorkspaceRead(WorkspaceBase):
    """Schema for reading workspace data."""

    id: UUID
    owner_id: UUID
    workflow_config_id: Optional[UUID]
    settings: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
