"""History models: RunRecord, InvocationRecord, AuditScoreRecord, etc.

These models track historical data for workflow runs, agent invocations,
and audit scores for analytics and evaluation purposes.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# RunRecord
# =============================================================================


class RunRecordBase(SQLModel):
    """Base run record fields."""

    run_id: str = Field(unique=True, index=True)
    story: str = Field(index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = Field(
        default="running", index=True
    )  # running, complete, failed, halted
    duration_s: Optional[float] = None
    total_tokens: int = Field(default=0)
    total_cost_usd: float = Field(default=0.0)
    final_post_path: Optional[str] = None
    final_score: Optional[float] = None


class RunRecord(UUIDModel, RunRecordBase, TimestampMixin, table=True):
    """RunRecord table - historical record of workflow runs."""

    __tablename__ = "run_records"

    user_id: UUID = Field(foreign_key="users.id", index=True)


class RunRecordCreate(RunRecordBase):
    """Schema for creating a new run record."""

    user_id: UUID


class RunRecordRead(RunRecordBase):
    """Schema for reading run record data."""

    id: UUID
    user_id: UUID
    created_at: datetime


# =============================================================================
# InvocationRecord
# =============================================================================


class InvocationRecordBase(SQLModel):
    """Base invocation record fields."""

    agent: str = Field(index=True)
    state: str = Field(index=True)
    persona: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_s: Optional[float] = None
    success: bool = Field(default=False)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    output_word_count: Optional[int] = None


class InvocationRecord(UUIDModel, InvocationRecordBase, TimestampMixin, table=True):
    """InvocationRecord table - record of single agent invocations."""

    __tablename__ = "invocation_records"

    run_id: str = Field(foreign_key="run_records.run_id", index=True)


class InvocationRecordCreate(InvocationRecordBase):
    """Schema for creating a new invocation record."""

    run_id: str


# =============================================================================
# AuditScoreRecord
# =============================================================================


class AuditScoreRecordBase(SQLModel):
    """Base audit score record fields."""

    auditor_agent: str = Field(index=True)
    target_agent: Optional[str] = None
    state: str = Field(index=True)
    overall_score: Optional[float] = None
    hook_score: Optional[float] = None
    specifics_score: Optional[float] = None
    voice_score: Optional[float] = None
    structure_score: Optional[float] = None
    feedback: Optional[str] = None


class AuditScoreRecord(UUIDModel, AuditScoreRecordBase, TimestampMixin, table=True):
    """AuditScoreRecord table - audit scores from auditor agents."""

    __tablename__ = "audit_score_records"

    run_id: str = Field(foreign_key="run_records.run_id", index=True)


class AuditScoreRecordCreate(AuditScoreRecordBase):
    """Schema for creating a new audit score record."""

    run_id: str


# =============================================================================
# PostIterationRecord
# =============================================================================


class PostIterationRecordBase(SQLModel):
    """Base post iteration record fields."""

    story: str = Field(index=True)
    iteration: int = Field(index=True)
    final_score: Optional[float] = None
    total_cost_usd: Optional[float] = None
    improvements: Optional[str] = None


class PostIterationRecord(
    UUIDModel, PostIterationRecordBase, TimestampMixin, table=True
):
    """PostIterationRecord table - iterations of the same story."""

    __tablename__ = "post_iteration_records"

    run_id: str = Field(foreign_key="run_records.run_id", index=True)


class PostIterationRecordCreate(PostIterationRecordBase):
    """Schema for creating a new post iteration record."""

    run_id: str
