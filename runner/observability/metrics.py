"""Metrics collection for observability.

Collects and aggregates metrics across agent calls:
- Latency percentiles (p50, p95, p99)
- Cost tracking per model/workspace
- Token usage trends
- Error rates

Usage:
    metrics = MetricsCollector()

    metrics.record_latency("claude-opus", 1500)  # 1500ms
    metrics.record_cost("claude-opus", 0.05)
    metrics.record_tokens("claude-opus", input=1000, output=500)

    summary = metrics.get_summary()
    print(f"p95 latency: {summary.latency_p95}ms")
"""

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class MetricsSummary:
    """Summary of collected metrics."""
    # Latency
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    latency_avg: float = 0.0

    # Cost
    total_cost: float = 0.0
    cost_by_model: dict[str, float] = field(default_factory=dict)

    # Tokens
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    tokens_by_model: dict[str, dict] = field(default_factory=dict)

    # Errors
    total_calls: int = 0
    total_errors: int = 0
    error_rate: float = 0.0

    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class MetricBucket:
    """A time-bucketed collection of metrics."""
    timestamp: datetime
    latencies: list[float] = field(default_factory=list)
    costs: list[float] = field(default_factory=list)
    input_tokens: list[int] = field(default_factory=list)
    output_tokens: list[int] = field(default_factory=list)
    error_count: int = 0
    call_count: int = 0


class MetricsCollector:
    """Collects and aggregates metrics.

    Maintains rolling time windows for metrics and provides
    percentile calculations.

    Usage:
        metrics = MetricsCollector(window_minutes=60)

        # Record metrics
        metrics.record_latency("claude-opus", 1500)
        metrics.record_cost("claude-opus", 0.05)
        metrics.record_tokens("claude-opus", 1000, 500)
        metrics.record_error("claude-opus")

        # Get summary
        summary = metrics.get_summary()
        print(f"p95 latency: {summary.latency_p95}ms")
        print(f"Total cost: ${summary.total_cost:.2f}")
    """

    def __init__(
        self,
        window_minutes: int = 60,
        bucket_size_minutes: int = 5,
    ):
        """Initialize metrics collector.

        Args:
            window_minutes: How long to keep metrics (default 60 min)
            bucket_size_minutes: Size of time buckets (default 5 min)
        """
        self.window_minutes = window_minutes
        self.bucket_size_minutes = bucket_size_minutes

        # Metrics by model
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._costs: dict[str, list[float]] = defaultdict(list)
        self._input_tokens: dict[str, list[int]] = defaultdict(list)
        self._output_tokens: dict[str, list[int]] = defaultdict(list)
        self._error_counts: dict[str, int] = defaultdict(int)
        self._call_counts: dict[str, int] = defaultdict(int)

        # Time-bucketed metrics for trends
        self._buckets: list[MetricBucket] = []
        self._last_bucket_time: Optional[datetime] = None

    def record_latency(self, model: str, latency_ms: float) -> None:
        """Record a latency measurement.

        Args:
            model: Model name
            latency_ms: Latency in milliseconds
        """
        self._latencies[model].append(latency_ms)
        self._ensure_bucket().latencies.append(latency_ms)

    def record_cost(self, model: str, cost: float) -> None:
        """Record a cost.

        Args:
            model: Model name
            cost: Cost in USD
        """
        self._costs[model].append(cost)
        self._ensure_bucket().costs.append(cost)

    def record_tokens(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Record token usage.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        self._input_tokens[model].append(input_tokens)
        self._output_tokens[model].append(output_tokens)

        bucket = self._ensure_bucket()
        bucket.input_tokens.append(input_tokens)
        bucket.output_tokens.append(output_tokens)

    def record_call(self, model: str, success: bool = True) -> None:
        """Record a call (for error rate tracking).

        Args:
            model: Model name
            success: Whether the call succeeded
        """
        self._call_counts[model] += 1
        bucket = self._ensure_bucket()
        bucket.call_count += 1

        if not success:
            self._error_counts[model] += 1
            bucket.error_count += 1

    def record_error(self, model: str) -> None:
        """Record an error.

        Args:
            model: Model name
        """
        self.record_call(model, success=False)

    def get_summary(self, model: Optional[str] = None) -> MetricsSummary:
        """Get metrics summary.

        Args:
            model: Optional model to filter by

        Returns:
            MetricsSummary with aggregated metrics
        """
        self._cleanup_old_buckets()

        if model:
            latencies = self._latencies.get(model, [])
            costs = self._costs.get(model, [])
            input_tokens = self._input_tokens.get(model, [])
            output_tokens = self._output_tokens.get(model, [])
            errors = self._error_counts.get(model, 0)
            calls = self._call_counts.get(model, 0)
        else:
            latencies = [l for ls in self._latencies.values() for l in ls]
            costs = [c for cs in self._costs.values() for c in cs]
            input_tokens = [t for ts in self._input_tokens.values() for t in ts]
            output_tokens = [t for ts in self._output_tokens.values() for t in ts]
            errors = sum(self._error_counts.values())
            calls = sum(self._call_counts.values())

        summary = MetricsSummary()

        if latencies:
            sorted_latencies = sorted(latencies)
            summary.latency_avg = statistics.mean(latencies)
            summary.latency_p50 = self._percentile(sorted_latencies, 50)
            summary.latency_p95 = self._percentile(sorted_latencies, 95)
            summary.latency_p99 = self._percentile(sorted_latencies, 99)

        summary.total_cost = sum(costs)
        summary.cost_by_model = {
            m: sum(cs) for m, cs in self._costs.items()
        }

        summary.total_input_tokens = sum(input_tokens)
        summary.total_output_tokens = sum(output_tokens)
        summary.tokens_by_model = {
            m: {
                "input": sum(self._input_tokens.get(m, [])),
                "output": sum(self._output_tokens.get(m, [])),
            }
            for m in set(self._input_tokens.keys()) | set(self._output_tokens.keys())
        }

        summary.total_calls = calls
        summary.total_errors = errors
        summary.error_rate = errors / calls if calls > 0 else 0.0

        if self._buckets:
            summary.start_time = self._buckets[0].timestamp
            summary.end_time = self._buckets[-1].timestamp

        return summary

    def get_trend(self, metric: str = "latency") -> list[dict]:
        """Get time-series trend data.

        Args:
            metric: Which metric to trend (latency, cost, tokens, errors)

        Returns:
            List of {timestamp, value} dicts
        """
        self._cleanup_old_buckets()

        trend = []
        for bucket in self._buckets:
            if metric == "latency":
                value = statistics.mean(bucket.latencies) if bucket.latencies else 0
            elif metric == "cost":
                value = sum(bucket.costs)
            elif metric == "tokens":
                value = sum(bucket.input_tokens) + sum(bucket.output_tokens)
            elif metric == "errors":
                value = bucket.error_count
            elif metric == "calls":
                value = bucket.call_count
            else:
                value = 0

            trend.append({
                "timestamp": bucket.timestamp.isoformat(),
                "value": value,
            })

        return trend

    def _ensure_bucket(self) -> MetricBucket:
        """Ensure current time bucket exists."""
        now = datetime.utcnow()
        bucket_time = now.replace(
            minute=(now.minute // self.bucket_size_minutes) * self.bucket_size_minutes,
            second=0,
            microsecond=0,
        )

        if not self._buckets or self._buckets[-1].timestamp != bucket_time:
            self._buckets.append(MetricBucket(timestamp=bucket_time))
            self._cleanup_old_buckets()

        return self._buckets[-1]

    def _cleanup_old_buckets(self) -> None:
        """Remove buckets older than the window."""
        cutoff = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        self._buckets = [b for b in self._buckets if b.timestamp >= cutoff]

    @staticmethod
    def _percentile(sorted_data: list[float], percentile: int) -> float:
        """Calculate percentile from sorted data."""
        if not sorted_data:
            return 0.0

        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f

        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


# Global metrics collector instance
_global_metrics: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = MetricsCollector()
    return _global_metrics
