"""Pydantic models for historical tracking."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class RunRecord(BaseModel):
    """Record of a workflow run."""

    run_id: str
    story: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: Literal["running", "complete", "failed", "halted"] = "running"
    duration_s: Optional[float] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    final_post_path: Optional[str] = None
    final_score: Optional[float] = None


class InvocationRecord(BaseModel):
    """Record of a single agent invocation."""

    run_id: str
    agent: str
    state: str
    persona: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_s: Optional[float] = None
    success: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    output_word_count: Optional[int] = None


class AuditScoreRecord(BaseModel):
    """Record of audit scores from an auditor agent."""

    run_id: str
    auditor_agent: str
    target_agent: Optional[str] = None
    state: str
    overall_score: Optional[float] = None
    hook_score: Optional[float] = None
    specifics_score: Optional[float] = None
    voice_score: Optional[float] = None
    structure_score: Optional[float] = None
    feedback: Optional[str] = None


class PostIterationRecord(BaseModel):
    """Record of a post iteration (same story, multiple runs)."""

    story: str
    run_id: str
    iteration: int
    final_score: Optional[float] = None
    total_cost_usd: Optional[float] = None
    improvements: Optional[str] = None


# ==========================================================================
# QUERY RESULT MODELS
# ==========================================================================


class AgentPerformance(BaseModel):
    """Agent performance metrics."""

    agent: str
    avg_score: float
    avg_hook: Optional[float] = None
    avg_specifics: Optional[float] = None
    avg_voice: Optional[float] = None
    avg_structure: Optional[float] = None
    sample_size: int


class CostBreakdown(BaseModel):
    """Cost breakdown for an agent."""

    agent: str
    invocations: int
    total_tokens: int
    total_cost: float
    avg_cost: float


class WeeklySummary(BaseModel):
    """Weekly summary of runs."""

    week: str
    runs: int
    avg_quality: Optional[float] = None
    total_cost: float
    total_tokens: int


class PostIteration(BaseModel):
    """Single iteration of a post."""

    iteration: int
    run_id: str
    final_score: Optional[float] = None
    total_cost: float
    improvements: Optional[str] = None
