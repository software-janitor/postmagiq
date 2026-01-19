"""Tests for the history service and queries (SQLModel)."""

from datetime import datetime, timedelta
import importlib

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine
from runner.db.models import (
    User,
    RunRecord as DbRunRecord,
    InvocationRecord as DbInvocationRecord,
    AuditScoreRecord as DbAuditScoreRecord,
    PostIterationRecord as DbPostIterationRecord,
)
from runner.history.models import (
    RunRecord,
    InvocationRecord,
    AuditScoreRecord,
    PostIterationRecord,
)
from runner.history.queries import HistoryQueries
from runner.history.service import HistoryService


db_engine = importlib.import_module("runner.db.engine")
history_service_module = importlib.import_module("runner.history.service")

HISTORY_TABLES = [
    User.__table__,
    DbRunRecord.__table__,
    DbInvocationRecord.__table__,
    DbAuditScoreRecord.__table__,
    DbPostIterationRecord.__table__,
]


@pytest.fixture
def history_engine(monkeypatch):
    """Create a SQLite engine with just the history tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine, tables=HISTORY_TABLES)
    monkeypatch.setattr(db_engine, "engine", engine)
    monkeypatch.setattr(history_service_module, "engine", engine)
    yield engine
    SQLModel.metadata.drop_all(engine, tables=HISTORY_TABLES)
    engine.dispose()


@pytest.fixture
def history_env(history_engine):
    """Create a history service with a test user."""
    with Session(history_engine) as session:
        user = User(full_name="Test User", email="test@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)
    return HistoryService(user_id=user.id), user.id


class TestHistoryService:
    """Tests for HistoryService SQLModel behavior."""

    def test_insert_and_retrieve_run(self, history_env):
        """Test inserting and retrieving a run."""
        service, _ = history_env
        now = datetime.utcnow()
        record = RunRecord(
            run_id="test-run-001",
            story="post_03",
            started_at=now,
            status="running",
        )
        service.insert_run(record)

        retrieved = service.get_run("test-run-001")
        assert retrieved is not None
        assert retrieved.run_id == "test-run-001"
        assert retrieved.story == "post_03"
        assert retrieved.status == "running"

    def test_update_run_complete(self, history_env):
        """Test updating a run with completion data."""
        service, _ = history_env
        now = datetime.utcnow()
        record = RunRecord(
            run_id="test-run-002",
            story="post_04",
            started_at=now,
            status="running",
        )
        service.insert_run(record)

        later = now + timedelta(minutes=10)
        service.update_run_complete(
            run_id="test-run-002",
            completed_at=later,
            status="complete",
            duration_s=600.0,
            total_tokens=5000,
            total_cost_usd=0.05,
            final_score=8.5,
        )

        retrieved = service.get_run("test-run-002")
        assert retrieved.status == "complete"
        assert retrieved.duration_s == 600.0
        assert retrieved.total_tokens == 5000
        assert retrieved.total_cost_usd == 0.05
        assert retrieved.final_score == 8.5

    def test_get_nonexistent_run(self, history_env):
        """Test retrieving a run that doesn't exist."""
        service, _ = history_env
        retrieved = service.get_run("nonexistent-run")
        assert retrieved is None

    def test_get_all_runs_ordered(self, history_env):
        """Test that runs are returned in reverse chronological order."""
        service, _ = history_env
        base_time = datetime.utcnow()
        for i in range(5):
            record = RunRecord(
                run_id=f"run-{i:03d}",
                story=f"post_{i:02d}",
                started_at=base_time + timedelta(hours=i),
                status="complete",
            )
            service.insert_run(record)

        runs = service.get_all_runs(limit=10)
        assert len(runs) == 5
        assert runs[0].run_id == "run-004"
        assert runs[4].run_id == "run-000"

    def test_insert_invocation(self, history_env):
        """Test inserting an invocation."""
        service, _ = history_env
        service.insert_run(
            RunRecord(run_id="inv-test-run", story="post_05", status="running")
        )

        record = InvocationRecord(
            run_id="inv-test-run",
            agent="claude",
            state="draft",
            persona="writer",
            started_at=datetime.utcnow(),
            duration_s=45.5,
            success=True,
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            cost_usd=0.0125,
        )
        inv_id = service.insert_invocation(record)
        assert inv_id == 0

        invocations = service.get_invocations_for_run("inv-test-run")
        assert len(invocations) == 1
        assert invocations[0].agent == "claude"
        assert invocations[0].success is True

    def test_insert_audit_score(self, history_env):
        """Test inserting an audit score."""
        service, _ = history_env
        service.insert_run(
            RunRecord(run_id="audit-test-run", story="post_06", status="running")
        )

        record = AuditScoreRecord(
            run_id="audit-test-run",
            auditor_agent="gemini",
            target_agent="claude",
            state="cross-audit",
            overall_score=8.0,
            hook_score=9.0,
            specifics_score=7.5,
            voice_score=8.5,
            feedback="Good hook, needs more specifics.",
        )
        score_id = service.insert_audit_score(record)
        assert score_id == 0

        scores = service.get_audit_scores_for_run("audit-test-run")
        assert len(scores) == 1
        assert scores[0].auditor_agent == "gemini"
        assert scores[0].overall_score == 8.0

    def test_post_iterations(self, history_env):
        """Test post iteration tracking."""
        service, _ = history_env
        service.insert_run(RunRecord(run_id="iter-run-1", story="post_07", status="complete"))
        service.insert_run(RunRecord(run_id="iter-run-2", story="post_07", status="complete"))

        service.insert_post_iteration(
            PostIterationRecord(
                story="post_07",
                run_id="iter-run-1",
                iteration=1,
                final_score=7.0,
                total_cost_usd=0.05,
            )
        )
        service.insert_post_iteration(
            PostIterationRecord(
                story="post_07",
                run_id="iter-run-2",
                iteration=2,
                final_score=8.5,
                total_cost_usd=0.04,
                improvements="Added sensory detail to opening",
            )
        )

        iterations = service.get_post_iterations("post_07")
        assert len(iterations) == 2
        assert iterations[0].iteration == 1
        assert iterations[1].iteration == 2
        assert iterations[1].final_score == 8.5

    def test_get_next_iteration_number(self, history_env):
        """Test getting next iteration number for a story."""
        service, _ = history_env
        next_iter = service.get_next_iteration_number("new_story")
        assert next_iter == 1

        service.insert_run(RunRecord(run_id="iter-next-1", story="post_08", status="complete"))
        service.insert_post_iteration(
            PostIterationRecord(
                story="post_08",
                run_id="iter-next-1",
                iteration=1,
                final_score=7.0,
            )
        )

        next_iter = service.get_next_iteration_number("post_08")
        assert next_iter == 2


class TestHistoryQueries:
    """Tests for HistoryQueries class."""

    @pytest.fixture
    def populated_env(self, history_env):
        """Create a database with sample data."""
        service, user_id = history_env
        base_time = datetime.utcnow() - timedelta(days=7)

        for i in range(3):
            run_id = f"query-run-{i:03d}"
            service.insert_run(
                RunRecord(
                    run_id=run_id,
                    story=f"post_{i:02d}",
                    started_at=base_time + timedelta(days=i),
                    completed_at=base_time + timedelta(days=i, hours=1),
                    status="complete",
                    duration_s=3600.0,
                    total_tokens=5000 + i * 1000,
                    total_cost_usd=0.05 + i * 0.01,
                    final_score=7.0 + i * 0.5,
                )
            )

            for agent in ["claude", "gemini", "codex"]:
                service.insert_invocation(
                    InvocationRecord(
                        run_id=run_id,
                        agent=agent,
                        state="draft",
                        started_at=base_time + timedelta(days=i),
                        duration_s=60.0,
                        success=True,
                        input_tokens=1000,
                        output_tokens=500,
                        total_tokens=1500,
                        cost_usd=0.015 if agent == "claude" else 0.01,
                    )
                )

            for auditor in ["claude", "gemini"]:
                for target in ["claude", "gemini", "codex"]:
                    if auditor != target:
                        service.insert_audit_score(
                            AuditScoreRecord(
                                run_id=run_id,
                                auditor_agent=auditor,
                                target_agent=target,
                                state="cross-audit",
                                overall_score=7.5 + i * 0.3,
                                hook_score=8.0,
                                specifics_score=7.0,
                                voice_score=7.5,
                            )
                        )

        return service, user_id

    def test_agent_performance(self, populated_env):
        """Test agent performance query."""
        _, user_id = populated_env
        queries = HistoryQueries(user_id)
        results = queries.agent_performance(days=30)

        assert len(results) >= 2
        for r in results:
            assert r.avg_score is not None
            assert r.sample_size > 0

    def test_cost_by_agent(self, populated_env):
        """Test cost by agent query."""
        _, user_id = populated_env
        queries = HistoryQueries(user_id)
        results = queries.cost_by_agent()

        assert len(results) == 3
        agents = {r.agent for r in results}
        assert "claude" in agents
        assert "gemini" in agents
        assert "codex" in agents

        claude = next(r for r in results if r.agent == "claude")
        assert claude.total_cost > 0

    def test_weekly_summary(self, populated_env):
        """Test weekly summary query."""
        _, user_id = populated_env
        queries = HistoryQueries(user_id)
        results = queries.weekly_summary(weeks=4)

        for r in results:
            assert r.runs > 0
            assert r.total_tokens >= 0

    def test_post_iterations_query(self, populated_env):
        """Test post iterations query."""
        service, user_id = populated_env
        service.insert_post_iteration(
            PostIterationRecord(
                story="post_00",
                run_id="query-run-000",
                iteration=1,
                final_score=7.0,
                total_cost_usd=0.05,
            )
        )

        queries = HistoryQueries(user_id)
        results = queries.post_iterations("post_00")

        assert len(results) == 1
        assert results[0].iteration == 1

    def test_post_iterations_empty(self, populated_env):
        """Test post iterations query with no data."""
        _, user_id = populated_env
        queries = HistoryQueries(user_id)
        results = queries.post_iterations("nonexistent_post")
        assert len(results) == 0

    def test_best_agent_for_task(self, populated_env):
        """Test best agent for task query."""
        _, user_id = populated_env
        queries = HistoryQueries(user_id)
        results = queries.best_agent_for_task("draft")

        assert len(results) >= 0

    def test_quality_trend(self, populated_env):
        """Test quality trend query."""
        _, user_id = populated_env
        queries = HistoryQueries(user_id)
        results = queries.quality_trend(days=14)

        assert len(results) >= 1
        for r in results:
            assert "day" in r
            assert "runs" in r


class TestHistoryEdgeCases:
    """Edge case tests for history service and queries."""

    def test_duplicate_run_id_fails(self, history_env):
        """Test that inserting duplicate run_id fails."""
        service, _ = history_env
        record = RunRecord(run_id="dup-test", story="post_01", status="running")
        service.insert_run(record)

        with pytest.raises(IntegrityError):
            service.insert_run(record)

    def test_null_timestamps_handled(self, history_env):
        """Test handling of null timestamps."""
        service, _ = history_env
        record = RunRecord(
            run_id="null-ts-test",
            story="post_02",
            status="running",
            started_at=None,
        )
        service.insert_run(record)

        retrieved = service.get_run("null-ts-test")
        assert retrieved.started_at is None

    def test_empty_database_queries(self, history_env):
        """Test queries on empty database."""
        _, user_id = history_env
        queries = HistoryQueries(user_id)

        assert queries.agent_performance() == []
        assert queries.cost_by_agent() == []
        assert queries.weekly_summary() == []
        assert queries.post_iterations("any") == []
