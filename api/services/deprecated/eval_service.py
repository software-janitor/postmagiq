"""Service for evaluation data aggregation."""

from typing import Optional
from uuid import UUID

from sqlmodel import select

from runner.db.engine import get_session
from runner.db.models import RunRecord
from runner.history.queries import HistoryQueries


class EvalService:
    """Aggregates evaluation data for API responses.

    Provides data formatted for the frontend dashboard.
    """

    def __init__(self, user_id: Optional[UUID] = None):
        """Initialize eval service.

        Args:
            user_id: Optional user filter for evaluation queries
        """
        self.user_id = user_id
        self.queries = HistoryQueries(user_id)

    def _list_runs(self, limit: int = 1000) -> list[RunRecord]:
        """List recent runs for summary stats."""
        with get_session() as session:
            statement = (
                select(RunRecord).order_by(RunRecord.started_at.desc()).limit(limit)
            )
            if self.user_id:
                statement = statement.where(RunRecord.user_id == self.user_id)
            return list(session.exec(statement).all())

    def get_agent_comparison(self, days: int = 30) -> dict:
        """Get agent performance comparison.

        Args:
            days: Number of days to look back

        Returns:
            Dict with period info and agent performance metrics
        """
        results = self.queries.agent_performance(days)
        return {
            "period_days": days,
            "agents": [
                {
                    "name": r.agent,
                    "avg_score": round(r.avg_score, 2) if r.avg_score else 0,
                    "avg_hook": round(r.avg_hook, 2) if r.avg_hook else None,
                    "avg_specifics": round(r.avg_specifics, 2)
                    if r.avg_specifics
                    else None,
                    "avg_voice": round(r.avg_voice, 2) if r.avg_voice else None,
                    "sample_size": r.sample_size,
                }
                for r in results
            ],
        }

    def get_cost_breakdown(self) -> dict:
        """Get cost breakdown by agent.

        Returns:
            Dict with total cost and per-agent breakdown
        """
        results = self.queries.cost_by_agent()
        total_cost = sum(r.total_cost for r in results)

        return {
            "total_cost_usd": round(total_cost, 2),
            "agents": [
                {
                    "name": r.agent,
                    "invocations": r.invocations,
                    "total_tokens": r.total_tokens,
                    "total_cost": round(r.total_cost, 2),
                    "avg_cost": round(r.avg_cost, 4),
                    "percentage": round(r.total_cost / total_cost * 100, 1)
                    if total_cost > 0
                    else 0,
                }
                for r in results
            ],
        }

    def get_quality_trend(self, weeks: int = 8) -> dict:
        """Get quality score trend over time.

        Args:
            weeks: Number of weeks to include

        Returns:
            Dict with weekly quality and cost data
        """
        results = self.queries.weekly_summary(weeks)
        return {
            "weeks": [
                {
                    "week": r.week,
                    "runs": r.runs,
                    "avg_quality": round(r.avg_quality, 2) if r.avg_quality else None,
                    "total_cost": round(r.total_cost, 2),
                }
                for r in results
            ],
        }

    def get_post_iterations(self, story: str) -> dict:
        """Get iteration history for a specific post.

        Args:
            story: Story identifier

        Returns:
            Dict with story name and iteration details
        """
        results = self.queries.post_iterations(story)
        return {
            "story": story,
            "iterations": [
                {
                    "iteration": r.iteration,
                    "run_id": r.run_id,
                    "final_score": r.final_score,
                    "total_cost": round(r.total_cost, 2) if r.total_cost else 0,
                    "improvements": r.improvements,
                }
                for r in results
            ],
        }

    def get_daily_trend(self, days: int = 30) -> dict:
        """Get daily quality trend.

        Args:
            days: Number of days to look back

        Returns:
            Dict with daily run counts and quality scores
        """
        results = self.queries.quality_trend(days)
        return {
            "period_days": days,
            "days": [
                {
                    "day": r["day"],
                    "runs": r["runs"],
                    "avg_score": round(r["avg_score"], 2) if r["avg_score"] else None,
                    "total_cost": round(r["total_cost"], 2),
                }
                for r in results
            ],
        }

    def get_best_agent_for_task(self, state: str) -> dict:
        """Get which agent performs best for a given task.

        Args:
            state: State/task name (e.g., "draft", "audit")

        Returns:
            Dict with state and ranked agents
        """
        results = self.queries.best_agent_for_task(state)
        return {
            "state": state,
            "agents": [
                {
                    "name": r.agent,
                    "avg_score": round(r.avg_score, 2) if r.avg_score else 0,
                    "sample_size": r.sample_size,
                }
                for r in results
            ],
        }

    def get_summary_stats(self) -> dict:
        """Get high-level summary statistics.

        Returns:
            Dict with overall stats
        """
        runs = self._list_runs(limit=1000)
        costs = self.queries.cost_by_agent()

        total_runs = len(runs)
        completed_runs = sum(1 for r in runs if r.status == "complete")
        total_cost = sum(c.total_cost for c in costs)
        total_tokens = sum(c.total_tokens for c in costs)

        # Calculate average score from completed runs with scores
        scores = [r.final_score for r in runs if r.final_score is not None]
        avg_score = sum(scores) / len(scores) if scores else None

        return {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "success_rate": round(completed_runs / total_runs * 100, 1)
            if total_runs > 0
            else 0,
            "total_cost_usd": round(total_cost, 2),
            "total_tokens": total_tokens,
            "avg_final_score": round(avg_score, 2) if avg_score else None,
        }
