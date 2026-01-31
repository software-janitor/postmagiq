"""Token tracking and aggregation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from runner.models import TokenUsage


@dataclass
class TokenRecord:
    """Single invocation token record."""

    timestamp: datetime
    agent: str
    state: str
    tokens: TokenUsage
    cost_usd: float
    context_window_max: int
    context_used_percent: float


@dataclass
class SessionTokens:
    """Cumulative session token tracking."""

    session_id: str
    agent: str
    invocations: int = 0
    cumulative_input: int = 0
    cumulative_output: int = 0
    total_cost_usd: float = 0.0
    context_window_max: int = 100000
    history: list[TokenRecord] = field(default_factory=list)

    @property
    def cumulative_total(self) -> int:
        return self.cumulative_input + self.cumulative_output

    @property
    def context_used_percent(self) -> float:
        if self.context_window_max == 0:
            return 0.0
        return (self.cumulative_total / self.context_window_max) * 100

    @property
    def context_remaining(self) -> int:
        return max(0, self.context_window_max - self.cumulative_total)

    def add_invocation(
        self, tokens: TokenUsage, cost: float, state: str
    ) -> TokenRecord:
        """Record a new invocation."""
        self.invocations += 1
        self.cumulative_input += tokens.input_tokens
        self.cumulative_output += tokens.output_tokens
        self.total_cost_usd += cost

        record = TokenRecord(
            timestamp=datetime.utcnow(),
            agent=self.agent,
            state=state,
            tokens=tokens,
            cost_usd=cost,
            context_window_max=self.context_window_max,
            context_used_percent=self.context_used_percent,
        )
        self.history.append(record)
        return record


@dataclass
class RunTokenSummary:
    """Full run token summary."""

    run_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    by_agent: dict[str, SessionTokens] = field(default_factory=dict)
    by_state: dict[str, int] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def add_record(self, record: TokenRecord):
        """Add a token record to the summary."""
        self.total_input_tokens += record.tokens.input_tokens
        self.total_output_tokens += record.tokens.output_tokens
        self.total_cost_usd += record.cost_usd

        if record.state not in self.by_state:
            self.by_state[record.state] = 0
        self.by_state[record.state] += record.tokens.total


class TokenTracker:
    """Central token tracking for a workflow run."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.summary = RunTokenSummary(run_id=run_id)
        self.sessions: dict[str, SessionTokens] = {}

    def get_or_create_session(
        self, agent: str, session_id: Optional[str] = None, context_window: int = 100000
    ) -> SessionTokens:
        """Get existing session or create new one."""
        key = session_id or agent
        if key not in self.sessions:
            self.sessions[key] = SessionTokens(
                session_id=key, agent=agent, context_window_max=context_window
            )
            self.summary.by_agent[agent] = self.sessions[key]
        return self.sessions[key]

    def record(
        self,
        agent: str,
        state: str,
        tokens: TokenUsage,
        cost: float,
        session_id: Optional[str] = None,
        context_window: int = 100000,
    ) -> TokenRecord:
        """Record token usage for an invocation."""
        session = self.get_or_create_session(agent, session_id, context_window)
        record = session.add_invocation(tokens, cost, state)
        self.summary.add_record(record)
        return record

    def get_summary(self) -> RunTokenSummary:
        """Get the current run summary."""
        return self.summary

    def check_context_health(self, agent: str) -> dict:
        """Check context window health for an agent."""
        if agent not in self.summary.by_agent:
            return {"status": "unknown", "message": "No records for agent"}

        session = self.summary.by_agent[agent]
        percent = session.context_used_percent

        if percent > 90:
            status = "critical"
            recommendation = "Consider summarizing context or starting new session"
        elif percent > 80:
            status = "warning"
            recommendation = "Context window filling up"
        elif percent > 60:
            status = "moderate"
            recommendation = "Context usage moderate"
        else:
            status = "healthy"
            recommendation = "Plenty of context remaining"

        return {
            "status": status,
            "used": session.cumulative_total,
            "max": session.context_window_max,
            "remaining": session.context_remaining,
            "percent_used": percent,
            "recommendation": recommendation,
        }
