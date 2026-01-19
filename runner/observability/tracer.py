"""Structured tracing for agent calls.

Provides detailed tracing of agent invocations including:
- Input/output capture
- Token usage
- Cost calculation
- Latency measurement
- Error tracking

Usage:
    tracer = AgentTracer()

    with tracer.trace_call("claude-opus", prompt) as span:
        result = await agent.invoke(prompt)
        span.set_output(result)
        span.set_tokens(input=1000, output=500)

    # Access span data
    print(f"Duration: {span.duration_ms}ms")
    print(f"Cost: ${span.cost:.4f}")
"""

import json
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# Model pricing for cost calculation (per 1M tokens)
MODEL_PRICING = {
    "claude-opus": {"input": 15.0, "output": 75.0},
    "claude-sonnet": {"input": 3.0, "output": 15.0},
    "claude-haiku": {"input": 0.25, "output": 1.25},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gemini-pro": {"input": 0.5, "output": 1.5},
    "gemini-flash": {"input": 0.075, "output": 0.3},
}


@dataclass
class SpanContext:
    """Context for a trace span."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class Span:
    """A single traced operation.

    Captures timing, input/output, token usage, and cost
    for an agent call.
    """
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    model: str = ""
    operation: str = "invoke"

    # Timing
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    # Input/Output (truncated for storage)
    input_preview: str = ""
    output_preview: str = ""
    input_length: int = 0
    output_length: int = 0

    # Tokens and cost
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0

    # Status
    status: str = "pending"  # pending, success, error
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    # Metadata
    metadata: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    def set_input(self, input_text: str, max_preview: int = 500) -> None:
        """Set input with truncation for storage."""
        self.input_length = len(input_text)
        self.input_preview = input_text[:max_preview]
        if len(input_text) > max_preview:
            self.input_preview += "..."

    def set_output(self, output: Any, max_preview: int = 500) -> None:
        """Set output with truncation for storage."""
        if isinstance(output, str):
            output_text = output
        else:
            output_text = str(output)

        self.output_length = len(output_text)
        self.output_preview = output_text[:max_preview]
        if len(output_text) > max_preview:
            self.output_preview += "..."

    def set_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Set token counts and calculate cost."""
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self._calculate_cost()

    def set_error(self, error: Exception) -> None:
        """Record an error."""
        self.status = "error"
        self.error_message = str(error)
        self.error_type = type(error).__name__

    def _calculate_cost(self) -> None:
        """Calculate cost based on tokens and model pricing."""
        pricing = MODEL_PRICING.get(self.model)
        if not pricing:
            return

        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        self.cost = input_cost + output_cost

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/logging."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "model": self.model,
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "input_preview": self.input_preview,
            "input_length": self.input_length,
            "output_preview": self.output_preview,
            "output_length": self.output_length,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "status": self.status,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "metadata": self.metadata,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


class AgentTracer:
    """Tracer for agent calls.

    Provides structured logging of all agent invocations with
    timing, token usage, and cost tracking.

    Usage:
        tracer = AgentTracer()

        with tracer.trace_call("claude-opus", prompt) as span:
            result = await agent.invoke(prompt)
            span.set_output(result)
            span.set_tokens(input=1000, output=500)

        # Or manually
        span = tracer.start_span("claude-opus", prompt)
        try:
            result = await agent.invoke(prompt)
            span.set_output(result)
            span.set_tokens(1000, 500)
            tracer.end_span(span, success=True)
        except Exception as e:
            tracer.end_span(span, error=e)
            raise
    """

    def __init__(
        self,
        log_inputs: bool = True,
        log_outputs: bool = True,
        max_preview_length: int = 500,
    ):
        """Initialize tracer.

        Args:
            log_inputs: Whether to log input previews
            log_outputs: Whether to log output previews
            max_preview_length: Max chars to store for previews
        """
        self.log_inputs = log_inputs
        self.log_outputs = log_outputs
        self.max_preview_length = max_preview_length
        self._spans: list[Span] = []

    @contextmanager
    def trace_call(
        self,
        model: str,
        input_text: str,
        operation: str = "invoke",
        **metadata,
    ):
        """Context manager for tracing a call.

        Args:
            model: Model name
            input_text: The input prompt
            operation: Operation type (invoke, stream, etc.)
            **metadata: Additional metadata

        Yields:
            Span object to record output and tokens
        """
        span = self.start_span(model, input_text, operation, **metadata)

        try:
            yield span
            self.end_span(span, success=True)
        except Exception as e:
            self.end_span(span, error=e)
            raise

    def start_span(
        self,
        model: str,
        input_text: str,
        operation: str = "invoke",
        **metadata,
    ) -> Span:
        """Start a new span.

        Args:
            model: Model name
            input_text: The input prompt
            operation: Operation type
            **metadata: Additional metadata

        Returns:
            Span object
        """
        span = Span(
            model=model,
            operation=operation,
            start_time=time.monotonic(),
            metadata=metadata,
        )

        if self.log_inputs:
            span.set_input(input_text, self.max_preview_length)

        logger.info(
            "agent_call_start",
            span_id=span.span_id,
            trace_id=span.trace_id,
            model=model,
            operation=operation,
            input_length=span.input_length,
            **metadata,
        )

        return span

    def end_span(
        self,
        span: Span,
        success: bool = True,
        error: Optional[Exception] = None,
    ) -> None:
        """End a span and log results.

        Args:
            span: The span to end
            success: Whether the operation succeeded
            error: Optional error that occurred
        """
        span.end_time = time.monotonic()

        if error:
            span.set_error(error)
        else:
            span.status = "success" if success else "error"

        self._spans.append(span)

        log_data = span.to_dict()

        if span.status == "success":
            logger.info(
                "agent_call_complete",
                **log_data,
            )
        else:
            logger.error(
                "agent_call_error",
                **log_data,
            )

    def get_recent_spans(self, limit: int = 100) -> list[Span]:
        """Get recent spans.

        Args:
            limit: Maximum number of spans to return

        Returns:
            List of recent spans
        """
        return self._spans[-limit:]

    def get_stats(self) -> dict:
        """Get aggregate statistics.

        Returns:
            Dict with aggregate stats
        """
        if not self._spans:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_latency_ms": 0.0,
                "error_rate": 0.0,
            }

        total_calls = len(self._spans)
        total_tokens = sum(s.total_tokens for s in self._spans)
        total_cost = sum(s.cost for s in self._spans)
        total_latency = sum(s.duration_ms for s in self._spans)
        error_count = sum(1 for s in self._spans if s.status == "error")

        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "avg_latency_ms": total_latency / total_calls,
            "error_rate": error_count / total_calls,
            "by_model": self._stats_by_model(),
        }

    def _stats_by_model(self) -> dict:
        """Get stats grouped by model."""
        by_model: dict[str, dict] = {}

        for span in self._spans:
            if span.model not in by_model:
                by_model[span.model] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "total_latency": 0.0,
                    "errors": 0,
                }

            stats = by_model[span.model]
            stats["calls"] += 1
            stats["tokens"] += span.total_tokens
            stats["cost"] += span.cost
            stats["total_latency"] += span.duration_ms
            if span.status == "error":
                stats["errors"] += 1

        # Calculate averages
        for model, stats in by_model.items():
            stats["avg_latency_ms"] = (
                stats["total_latency"] / stats["calls"]
                if stats["calls"] > 0 else 0
            )
            stats["error_rate"] = (
                stats["errors"] / stats["calls"]
                if stats["calls"] > 0 else 0
            )
            del stats["total_latency"]

        return by_model
