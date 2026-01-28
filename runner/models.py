"""Pydantic models for LLM outputs and workflow data structures."""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class TokenUsage(BaseModel):
    """Token counts from an agent invocation."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class AgentResult(BaseModel):
    """Validated result from any agent invocation."""

    success: bool
    content: str
    tokens: TokenUsage
    duration_s: float = 0.0
    session_id: Optional[str] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


class AuditIssue(BaseModel):
    """Single issue from an audit."""

    severity: Literal["critical", "major", "minor"]
    issue: str
    fix: str
    line_reference: Optional[str] = None


class AuditResult(BaseModel):
    """Structured output from quality gate audits."""

    score: int = Field(ge=1, le=10)
    decision: Literal["proceed", "retry", "halt"]
    feedback: str
    issues: list[AuditIssue] = Field(default_factory=list)

    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)


class CircuitBreakerDecision(BaseModel):
    """Orchestrator's response when circuit breaker triggers."""

    decision: Literal["force_complete", "retry_different", "halt", "dump_context"]
    reasoning: str
    use_output: Optional[str] = None
    retry_from: Optional[str] = None
    retry_guidance: Optional[str] = None


class FanOutResult(BaseModel):
    """Result from a fan-out state execution."""

    agent: str
    status: Literal["success", "failed", "timeout"]
    output_path: Optional[str] = None
    content: Optional[str] = None
    tokens: Optional[TokenUsage] = None
    cost_usd: float = 0.0
    duration_s: float = 0.0
    error: Optional[str] = None


class StateResult(BaseModel):
    """Result from executing a state."""

    state_name: str
    transition: str
    outputs: dict[str, FanOutResult] = Field(default_factory=dict)
    duration_s: float = 0.0
    total_tokens: Optional[TokenUsage] = None
    total_cost_usd: float = 0.0


class RunManifest(BaseModel):
    """Metadata for a workflow run."""

    run_id: str
    story: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: Literal["running", "complete", "failed", "halted"] = "running"
    final_state: Optional[str] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    config_hash: Optional[str] = None
