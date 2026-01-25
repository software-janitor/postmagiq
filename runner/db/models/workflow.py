"""Workflow models: WorkflowRun, WorkflowOutput, WorkflowSession, etc."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# WorkflowRun
# =============================================================================

class WorkflowRunBase(SQLModel):
    """Base workflow run fields."""

    run_id: str = Field(unique=True, index=True)
    story_name: Optional[str] = Field(default=None)
    status: str = Field(default="running", index=True)
    current_state: Optional[str] = None
    total_transitions: Optional[int] = Field(default=0)
    total_tokens: Optional[int] = Field(default=0)
    total_cost: Optional[float] = Field(default=0.0)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WorkflowRun(UUIDModel, WorkflowRunBase, table=True):
    """WorkflowRun table - track workflow executions."""

    __tablename__ = "workflow_runs"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class WorkflowRunCreate(SQLModel):
    """Schema for creating a new workflow run."""

    user_id: UUID
    run_id: str
    story_name: Optional[str] = None
    workspace_id: Optional[UUID] = None


class WorkflowRunRead(WorkflowRunBase):
    """Schema for reading workflow run data."""

    id: UUID
    user_id: UUID
    workspace_id: Optional[UUID]


# =============================================================================
# WorkflowOutput
# =============================================================================

class WorkflowOutputBase(SQLModel):
    """Base workflow output fields."""

    state_name: str = Field(index=True)
    agent: Optional[str] = None
    output_type: str
    content: str


class WorkflowOutput(UUIDModel, WorkflowOutputBase, TimestampMixin, table=True):
    """WorkflowOutput table - outputs at each workflow step."""

    __tablename__ = "workflow_outputs"

    run_id: str = Field(foreign_key="workflow_runs.run_id", index=True)


class WorkflowOutputCreate(WorkflowOutputBase):
    """Schema for creating a new workflow output."""

    run_id: str


# =============================================================================
# WorkflowSession
# =============================================================================

class WorkflowSessionBase(SQLModel):
    """Base workflow session fields."""

    agent_name: str = Field(index=True)
    session_id: str


class WorkflowSession(UUIDModel, WorkflowSessionBase, TimestampMixin, table=True):
    """WorkflowSession table - CLI sessions for agents."""

    __tablename__ = "workflow_sessions"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    run_id: Optional[str] = Field(default=None, foreign_key="workflow_runs.run_id", index=True)


class WorkflowSessionCreate(WorkflowSessionBase):
    """Schema for creating a new workflow session."""

    user_id: UUID
    run_id: Optional[str] = None


# =============================================================================
# WorkflowStateMetric
# =============================================================================

class WorkflowStateMetricBase(SQLModel):
    """Base workflow state metric fields."""

    state_name: str = Field(index=True)
    agent: str = Field(index=True)
    tokens_input: int = Field(default=0)
    tokens_output: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    duration_s: float = Field(default=0.0)


class WorkflowStateMetric(UUIDModel, WorkflowStateMetricBase, TimestampMixin, table=True):
    """WorkflowStateMetric table - per-state, per-agent token/cost tracking."""

    __tablename__ = "workflow_state_metrics"

    run_id: str = Field(foreign_key="workflow_runs.run_id", index=True)


class WorkflowStateMetricCreate(WorkflowStateMetricBase):
    """Schema for creating a new workflow state metric."""

    run_id: str


# =============================================================================
# WorkflowPersona
# =============================================================================

class WorkflowPersonaBase(SQLModel):
    """Base workflow persona fields."""

    name: str
    slug: str = Field(index=True)
    description: Optional[str] = None
    content: str
    is_system: bool = Field(default=False)
    model_tier: Optional[str] = None


class WorkflowPersona(UUIDModel, WorkflowPersonaBase, TimestampMixin, table=True):
    """WorkflowPersona table - persona definitions for workflow agents."""

    __tablename__ = "workflow_personas"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )

    # Optional FK to voice profile for voice-specific personas
    voice_profile_id: Optional[UUID] = Field(
        default=None,
        foreign_key="voice_profiles.id",
        index=True,
    )


class WorkflowPersonaCreate(WorkflowPersonaBase):
    """Schema for creating a new workflow persona."""

    user_id: UUID
    workspace_id: Optional[UUID] = None
    voice_profile_id: Optional[UUID] = None


class WorkflowPersonaRead(WorkflowPersonaBase):
    """Schema for reading workflow persona data."""

    id: UUID
    user_id: UUID
    workspace_id: Optional[UUID]
    voice_profile_id: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]
