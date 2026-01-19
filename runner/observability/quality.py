"""Quality monitoring for generated content.

Monitors quality metrics over time:
- Voice consistency/drift
- Character visual consistency
- Engagement correlation
- Content quality scores

Usage:
    monitor = QualityMonitor()

    # Record quality score
    monitor.record_score(
        content_id="123",
        score_type="voice_consistency",
        score=0.85,
    )

    # Check for drift
    if monitor.detect_drift("voice_consistency"):
        alert("Voice drift detected!")
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class ScoreType(str, Enum):
    """Types of quality scores."""
    VOICE_CONSISTENCY = "voice_consistency"
    CHARACTER_CONSISTENCY = "character_consistency"
    ENGAGEMENT = "engagement"
    READABILITY = "readability"
    BRAND_ALIGNMENT = "brand_alignment"


@dataclass
class QualityScore:
    """A single quality measurement."""
    content_id: str
    score_type: str
    score: float  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class DriftAlert:
    """Alert for quality drift."""
    score_type: str
    current_avg: float
    baseline_avg: float
    drift_percentage: float
    timestamp: datetime
    message: str


class QualityMonitor:
    """Monitor content quality over time.

    Tracks quality scores and detects drift from baseline.

    Usage:
        monitor = QualityMonitor()

        # Record scores
        monitor.record_score("content-1", "voice_consistency", 0.85)
        monitor.record_score("content-2", "voice_consistency", 0.82)

        # Check for drift
        drift = monitor.detect_drift("voice_consistency")
        if drift:
            print(f"Drift detected: {drift.message}")

        # Get summary
        summary = monitor.get_summary("voice_consistency")
        print(f"Average: {summary['avg']:.2f}")
    """

    def __init__(
        self,
        baseline_window_days: int = 30,
        drift_threshold: float = 0.10,  # 10% drift triggers alert
        min_samples: int = 10,
    ):
        """Initialize quality monitor.

        Args:
            baseline_window_days: Days to use for baseline calculation
            drift_threshold: Percentage drift to trigger alert
            min_samples: Minimum samples needed for drift detection
        """
        self.baseline_window_days = baseline_window_days
        self.drift_threshold = drift_threshold
        self.min_samples = min_samples

        # Scores by type
        self._scores: dict[str, list[QualityScore]] = defaultdict(list)

        # Baselines (cached)
        self._baselines: dict[str, float] = {}
        self._baseline_updated: dict[str, datetime] = {}

    def record_score(
        self,
        content_id: str,
        score_type: str,
        score: float,
        **metadata,
    ) -> None:
        """Record a quality score.

        Args:
            content_id: ID of the content
            score_type: Type of score (voice_consistency, etc.)
            score: Score value (0.0 to 1.0)
            **metadata: Additional metadata
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0 and 1, got {score}")

        quality_score = QualityScore(
            content_id=content_id,
            score_type=score_type,
            score=score,
            metadata=metadata,
        )
        self._scores[score_type].append(quality_score)

    def get_summary(
        self,
        score_type: str,
        window_days: Optional[int] = None,
    ) -> dict:
        """Get summary statistics for a score type.

        Args:
            score_type: Type of score to summarize
            window_days: Optional window to limit (default: all)

        Returns:
            Dict with avg, min, max, std, count
        """
        scores = self._get_scores_in_window(score_type, window_days)

        if not scores:
            return {
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std": 0.0,
                "count": 0,
            }

        values = [s.score for s in scores]

        return {
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "count": len(values),
        }

    def detect_drift(
        self,
        score_type: str,
        recent_window_days: int = 7,
    ) -> Optional[DriftAlert]:
        """Detect quality drift from baseline.

        Args:
            score_type: Type of score to check
            recent_window_days: Window for recent scores

        Returns:
            DriftAlert if drift detected, None otherwise
        """
        # Get baseline
        baseline = self._get_baseline(score_type)
        if baseline is None:
            return None

        # Get recent scores
        recent_scores = self._get_scores_in_window(score_type, recent_window_days)
        if len(recent_scores) < self.min_samples:
            return None

        recent_avg = statistics.mean([s.score for s in recent_scores])

        # Calculate drift percentage
        drift = (baseline - recent_avg) / baseline if baseline > 0 else 0

        if abs(drift) >= self.drift_threshold:
            direction = "declined" if drift > 0 else "improved"
            return DriftAlert(
                score_type=score_type,
                current_avg=recent_avg,
                baseline_avg=baseline,
                drift_percentage=drift * 100,
                timestamp=datetime.utcnow(),
                message=f"{score_type} has {direction} by {abs(drift)*100:.1f}% "
                        f"(baseline: {baseline:.2f}, current: {recent_avg:.2f})",
            )

        return None

    def get_trend(
        self,
        score_type: str,
        window_days: int = 30,
        bucket_days: int = 1,
    ) -> list[dict]:
        """Get time-series trend for a score type.

        Args:
            score_type: Type of score
            window_days: Total window
            bucket_days: Size of each bucket

        Returns:
            List of {date, avg, count} dicts
        """
        scores = self._get_scores_in_window(score_type, window_days)

        # Group by date bucket
        buckets: dict[str, list[float]] = defaultdict(list)
        for score in scores:
            bucket_date = score.timestamp.strftime("%Y-%m-%d")
            buckets[bucket_date].append(score.score)

        # Calculate averages
        trend = []
        for date, values in sorted(buckets.items()):
            trend.append({
                "date": date,
                "avg": statistics.mean(values),
                "count": len(values),
            })

        return trend

    def get_low_quality_content(
        self,
        score_type: str,
        threshold: float = 0.7,
        limit: int = 10,
    ) -> list[QualityScore]:
        """Get content with low quality scores.

        Args:
            score_type: Type of score
            threshold: Score threshold
            limit: Max items to return

        Returns:
            List of QualityScore objects below threshold
        """
        scores = self._scores.get(score_type, [])
        low_scores = [s for s in scores if s.score < threshold]
        low_scores.sort(key=lambda s: s.score)
        return low_scores[:limit]

    def _get_baseline(self, score_type: str) -> Optional[float]:
        """Get or calculate baseline for a score type."""
        now = datetime.utcnow()

        # Check if we have a recent cached baseline
        if score_type in self._baselines:
            last_update = self._baseline_updated.get(score_type)
            if last_update and (now - last_update) < timedelta(days=1):
                return self._baselines[score_type]

        # Calculate baseline from historical data
        scores = self._get_scores_in_window(score_type, self.baseline_window_days)
        if len(scores) < self.min_samples:
            return None

        baseline = statistics.mean([s.score for s in scores])
        self._baselines[score_type] = baseline
        self._baseline_updated[score_type] = now

        return baseline

    def _get_scores_in_window(
        self,
        score_type: str,
        window_days: Optional[int] = None,
    ) -> list[QualityScore]:
        """Get scores within a time window."""
        scores = self._scores.get(score_type, [])

        if window_days is None:
            return scores

        cutoff = datetime.utcnow() - timedelta(days=window_days)
        return [s for s in scores if s.timestamp >= cutoff]


# Global quality monitor instance
_global_monitor: Optional[QualityMonitor] = None


def get_quality_monitor() -> QualityMonitor:
    """Get the global quality monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = QualityMonitor()
    return _global_monitor
