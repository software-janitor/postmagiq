"""Admin analytics models.

Daily cost rollups per workspace for SaaS owner analytics.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


class WorkspaceDailyCostsBase(SQLModel):
    """Base fields for workspace daily costs."""

    cost_date: date = Field(index=True)
    total_cost_usd: float = Field(default=0.0)
    total_tokens: int = Field(default=0)
    run_count: int = Field(default=0)
    successful_runs: int = Field(default=0)
    failed_runs: int = Field(default=0)


class WorkspaceDailyCosts(UUIDModel, WorkspaceDailyCostsBase, TimestampMixin, table=True):
    """Daily cost rollup per workspace."""

    __tablename__ = "workspace_daily_costs"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)


class WorkspaceDailyCostsCreate(WorkspaceDailyCostsBase):
    """Schema for creating workspace daily costs."""

    workspace_id: UUID


class WorkspaceDailyCostsRead(WorkspaceDailyCostsBase):
    """Schema for reading workspace daily costs."""

    id: UUID
    workspace_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
