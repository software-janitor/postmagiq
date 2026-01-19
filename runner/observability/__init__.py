"""Observability module for logging, metrics, and tracing.

This module provides:
- Structured logging for agent calls
- Metrics tracking (latency, cost, tokens)
- Quality monitoring (voice drift, consistency)
- Alerting on anomalies

Usage:
    from runner.observability import AgentTracer, MetricsCollector

    tracer = AgentTracer()
    metrics = MetricsCollector()

    with tracer.trace_call("claude-opus", prompt) as span:
        result = await agent.invoke(prompt)
        span.set_output(result)
        span.set_tokens(input=1000, output=500)

    metrics.record_latency("claude-opus", span.duration_ms)
    metrics.record_cost("claude-opus", span.cost)
"""

from runner.observability.tracer import (
    AgentTracer,
    Span,
    SpanContext,
)
from runner.observability.metrics import (
    MetricsCollector,
    MetricsSummary,
)
from runner.observability.quality import (
    QualityMonitor,
    QualityScore,
)

__all__ = [
    "AgentTracer",
    "Span",
    "SpanContext",
    "MetricsCollector",
    "MetricsSummary",
    "QualityMonitor",
    "QualityScore",
]
