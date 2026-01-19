"""Historical tracking module for workflow runs.

This module provides SQLModel-backed history tracking via HistoryService.

Usage:
    from runner.history import HistoryService

    service = HistoryService(user_id=user_id)
    service.insert_run(record)
"""

from runner.history.service import HistoryService
from runner.history.models import (
    RunRecord,
    InvocationRecord,
    AuditScoreRecord,
    PostIterationRecord,
    AgentPerformance,
    CostBreakdown,
    WeeklySummary,
    PostIteration,
)
from runner.history.queries import HistoryQueries

__all__ = [
    "HistoryService",
    "HistoryQueries",
    "RunRecord",
    "InvocationRecord",
    "AuditScoreRecord",
    "PostIterationRecord",
    "AgentPerformance",
    "CostBreakdown",
    "WeeklySummary",
    "PostIteration",
]
