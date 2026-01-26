"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


class RunSummary(BaseModel):
    """Summary of a workflow run."""

    run_id: str
    story: str = "unknown"
    status: Literal["running", "complete", "failed", "halted", "error"]
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    credits: Optional[int] = None  # Credits equivalent (for users with show_costs=False)
    final_state: Optional[str] = None
    config_hash: Optional[str] = None


class StateLogEntry(BaseModel):
    """Single entry from state_log.jsonl."""

    ts: str
    run_id: str
    event: str
    state: Optional[str] = None
    type: Optional[str] = None
    transition: Optional[str] = None
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    duration_s: Optional[float] = None
    outputs: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class TokenBreakdown(BaseModel):
    """Token usage breakdown."""

    total_input: int = 0
    total_output: int = 0
    total_cost_usd: float = 0.0
    by_agent: dict[str, dict[str, Any]] = Field(default_factory=dict)  # {agent: {input, output, total, cost_usd}}
    by_state: dict[str, dict[str, Any]] = Field(default_factory=dict)  # {state: {tokens, cost_usd}}


class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow."""

    story: str
    input_path: Optional[str] = None
    content: Optional[str] = None  # Raw content to process (alternative to input_path)
    interactive: bool = False
    config: Optional[str] = None  # Workflow config slug (e.g., "groq-production")


class WorkflowStepRequest(BaseModel):
    """Request to execute a single workflow step."""

    story: str
    step: str
    run_id: Optional[str] = None  # If provided, continues an existing run


class ApprovalRequest(BaseModel):
    """Request for human approval response."""

    decision: Literal["approved", "feedback", "abort"]
    feedback: Optional[str] = None


class WorkflowStatus(BaseModel):
    """Current workflow execution status."""

    running: bool = False
    run_id: Optional[str] = None
    current_state: Optional[str] = None
    story: Optional[str] = None
    started_at: Optional[datetime] = None
    awaiting_approval: bool = False


class ConfigUpdateRequest(BaseModel):
    """Request to update workflow config."""

    config: str  # YAML string


class ConfigValidationResult(BaseModel):
    """Result of config validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ArtifactInfo(BaseModel):
    """Information about a workflow artifact."""

    path: str
    name: str
    type: Literal["draft", "audit", "final", "input", "other"]
    size_bytes: int
    modified_at: datetime
