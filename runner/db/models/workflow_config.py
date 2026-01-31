"""Workflow configuration models.

Implements dynamic workflow configuration for GUI-selectable configs
with deployment environment filtering.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID

from sqlmodel import Field, SQLModel, Column, JSON

from runner.db.models.base import UUIDModel, TimestampMixin


class WorkflowEnvironment(str, Enum):
    """Deployment environment for workflow configs."""

    production = "production"
    development = "development"
    staging = "staging"


# =============================================================================
# Workflow Configuration
# =============================================================================


class WorkflowConfigBase(SQLModel):
    """Base fields for workflow configuration."""

    # Identification
    name: str = Field(index=True)  # Display name, e.g., "Groq Production"
    slug: str = Field(unique=True, index=True)  # URL-safe ID, e.g., "groq-production"
    description: Optional[str] = None

    # Configuration
    config_file: (
        str  # Path relative to workflows/configs/, e.g., "groq-production.yaml"
    )
    environment: WorkflowEnvironment = Field(default=WorkflowEnvironment.production)

    # Features (stored as JSON for flexibility)
    features: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    # Tier restriction (null = available to all)
    tier_required: Optional[str] = Field(default=None, index=True)

    # Status
    enabled: bool = Field(default=True, index=True)
    is_default: bool = Field(default=False)


class WorkflowConfig(UUIDModel, WorkflowConfigBase, TimestampMixin, table=True):
    """Workflow configuration table.

    Stores metadata about available workflow configurations.
    The actual config YAML files are stored in workflows/configs/.
    This table enables:
    - GUI selection of workflow configs
    - Deployment environment filtering
    - Tier-based access control
    """

    __tablename__ = "workflow_configs"


class WorkflowConfigCreate(WorkflowConfigBase):
    """Schema for creating a workflow configuration."""

    pass


class WorkflowConfigRead(WorkflowConfigBase):
    """Schema for reading workflow configuration data."""

    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


class WorkflowConfigUpdate(SQLModel):
    """Schema for updating a workflow configuration."""

    name: Optional[str] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    tier_required: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
