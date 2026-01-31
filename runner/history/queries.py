"""Evaluation queries against history records (SQLModel)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import select

from runner.db.engine import get_session
from runner.db.models import (
    RunRecord,
    InvocationRecord,
    AuditScoreRecord,
    PostIterationRecord,
)
from runner.history.models import (
    AgentPerformance,
    CostBreakdown,
    WeeklySummary,
    PostIteration,
)


class HistoryQueries:
    """Evaluation queries against history records."""

    def __init__(self, user_id: Optional[UUID] = None):
        self.user_id = user_id

    def _run_ids_since(self, since: datetime) -> list[str]:
        """Return run_ids for runs after `since`, optionally filtered by user."""
        with get_session() as session:
            statement = select(RunRecord).where(RunRecord.started_at >= since)
            if self.user_id:
                statement = statement.where(RunRecord.user_id == self.user_id)
            runs = session.exec(statement).all()
            return [r.run_id for r in runs if r.run_id]

    def _runs_for_user(self) -> list[RunRecord]:
        """Return all runs for user (or all if user_id is None)."""
        with get_session() as session:
            statement = select(RunRecord)
            if self.user_id:
                statement = statement.where(RunRecord.user_id == self.user_id)
            return list(session.exec(statement).all())

    def agent_performance(self, days: int = 30) -> list[AgentPerformance]:
        """Get agent performance comparison over last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        run_ids = set(self._run_ids_since(since))
        if not run_ids:
            return []

        with get_session() as session:
            scores = session.exec(
                select(AuditScoreRecord).where(AuditScoreRecord.run_id.in_(run_ids))
            ).all()

        grouped = defaultdict(list)
        for score in scores:
            if not score.target_agent or score.overall_score is None:
                continue
            grouped[score.target_agent].append(score)

        results = []
        for agent, items in grouped.items():
            sample_size = len(items)
            results.append(
                AgentPerformance(
                    agent=agent,
                    avg_score=sum(s.overall_score or 0 for s in items) / sample_size
                    if sample_size
                    else 0.0,
                    avg_hook=_avg_optional(items, "hook_score"),
                    avg_specifics=_avg_optional(items, "specifics_score"),
                    avg_voice=_avg_optional(items, "voice_score"),
                    avg_structure=_avg_optional(items, "structure_score"),
                    sample_size=sample_size,
                )
            )

        return sorted(results, key=lambda r: r.avg_score or 0, reverse=True)

    def cost_by_agent(self) -> list[CostBreakdown]:
        """Get cost breakdown by agent across all runs."""
        with get_session() as session:
            statement = select(InvocationRecord)
            if self.user_id:
                run_ids = {r.run_id for r in self._runs_for_user()}
                if not run_ids:
                    return []
                statement = statement.where(InvocationRecord.run_id.in_(run_ids))
            invocations = session.exec(statement).all()

        grouped = defaultdict(list)
        for inv in invocations:
            grouped[inv.agent].append(inv)

        results = []
        for agent, items in grouped.items():
            total_tokens = sum(i.total_tokens or 0 for i in items)
            total_cost = sum(i.cost_usd or 0 for i in items)
            invocations_count = len(items)
            results.append(
                CostBreakdown(
                    agent=agent,
                    invocations=invocations_count,
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    avg_cost=total_cost / invocations_count
                    if invocations_count
                    else 0.0,
                )
            )
        return sorted(results, key=lambda r: r.total_cost or 0, reverse=True)

    def weekly_summary(self, weeks: int = 12) -> list[WeeklySummary]:
        """Get weekly summary of runs, cost, and quality."""
        since = datetime.utcnow() - timedelta(weeks=weeks)
        runs = [
            run
            for run in self._runs_for_user()
            if run.status == "complete" and run.started_at and run.started_at >= since
        ]

        grouped: dict[str, list[RunRecord]] = defaultdict(list)
        for run in runs:
            week_key = run.started_at.strftime("%Y-%W")
            grouped[week_key].append(run)

        results = []
        for week, items in grouped.items():
            runs_count = len(items)
            avg_quality = _avg_optional(items, "final_score")
            total_cost = sum(r.total_cost_usd or 0 for r in items)
            total_tokens = sum(r.total_tokens or 0 for r in items)
            results.append(
                WeeklySummary(
                    week=week,
                    runs=runs_count,
                    avg_quality=avg_quality,
                    total_cost=total_cost,
                    total_tokens=total_tokens,
                )
            )
        return sorted(results, key=lambda r: r.week)

    def post_iterations(self, story: str) -> list[PostIteration]:
        """Get iteration history for a specific post/story."""
        with get_session() as session:
            statement = select(PostIterationRecord).where(
                PostIterationRecord.story == story
            )
            if self.user_id:
                run_ids = {r.run_id for r in self._runs_for_user()}
                if run_ids:
                    statement = statement.where(PostIterationRecord.run_id.in_(run_ids))
            records = session.exec(
                statement.order_by(PostIterationRecord.iteration)
            ).all()

        return [
            PostIteration(
                iteration=r.iteration,
                run_id=r.run_id,
                final_score=r.final_score,
                total_cost=r.total_cost_usd or 0,
                improvements=r.improvements,
            )
            for r in records
        ]

    def best_agent_for_task(self, state: str) -> list[AgentPerformance]:
        """Get which agent performs best for a given state (draft, audit, etc)."""
        run_ids = {r.run_id for r in self._runs_for_user()} if self.user_id else None
        with get_session() as session:
            inv_statement = select(InvocationRecord).where(
                InvocationRecord.state == state
            )
            if run_ids:
                inv_statement = inv_statement.where(
                    InvocationRecord.run_id.in_(run_ids)
                )
            invocations = session.exec(inv_statement).all()

            score_statement = select(AuditScoreRecord)
            if run_ids:
                score_statement = score_statement.where(
                    AuditScoreRecord.run_id.in_(run_ids)
                )
            scores = session.exec(score_statement).all()

        scores_by_run_agent = defaultdict(list)
        for score in scores:
            if score.target_agent:
                scores_by_run_agent[(score.run_id, score.target_agent)].append(score)

        grouped = defaultdict(list)
        for inv in invocations:
            key = (inv.run_id, inv.agent)
            for score in scores_by_run_agent.get(key, []):
                if score.overall_score is None:
                    continue
                grouped[inv.agent].append(score)

        results = []
        for agent, items in grouped.items():
            sample_size = len(items)
            results.append(
                AgentPerformance(
                    agent=agent,
                    avg_score=sum(s.overall_score or 0 for s in items) / sample_size
                    if sample_size
                    else 0.0,
                    avg_hook=_avg_optional(items, "hook_score"),
                    avg_specifics=_avg_optional(items, "specifics_score"),
                    avg_voice=_avg_optional(items, "voice_score"),
                    avg_structure=_avg_optional(items, "structure_score"),
                    sample_size=sample_size,
                )
            )
        return sorted(results, key=lambda r: r.avg_score or 0, reverse=True)

    def quality_trend(self, days: int = 30) -> list[dict]:
        """Get daily quality trend over the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        runs = [
            run
            for run in self._runs_for_user()
            if run.status == "complete" and run.started_at and run.started_at >= since
        ]

        grouped = defaultdict(list)
        for run in runs:
            day_key = run.started_at.date().isoformat()
            grouped[day_key].append(run)

        results = []
        for day, items in sorted(grouped.items()):
            results.append(
                {
                    "day": day,
                    "runs": len(items),
                    "avg_score": _avg_optional(items, "final_score"),
                    "total_cost": sum(r.total_cost_usd or 0 for r in items),
                }
            )
        return results

    def runs_for_story(self, story: str, limit: int = 10) -> list[dict]:
        """Get recent runs for a specific story."""
        with get_session() as session:
            statement = select(RunRecord).where(RunRecord.story == story)
            if self.user_id:
                statement = statement.where(RunRecord.user_id == self.user_id)
            records = session.exec(
                statement.order_by(RunRecord.started_at.desc()).limit(limit)
            ).all()
            return [
                {
                    "run_id": r.run_id,
                    "started_at": r.started_at,
                    "status": r.status,
                    "duration_s": r.duration_s,
                    "total_tokens": r.total_tokens,
                    "total_cost_usd": r.total_cost_usd,
                    "final_score": r.final_score,
                }
                for r in records
            ]


def _avg_optional(items, field: str) -> Optional[float]:
    """Average numeric field across records."""
    values = [
        getattr(item, field) for item in items if getattr(item, field) is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)
