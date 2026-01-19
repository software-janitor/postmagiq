"""SQLModel-based history service.

Provides the same API as HistoryDatabase but uses PostgreSQL via SQLModel.
This is a drop-in replacement for the legacy SQLite-based HistoryDatabase.

Usage:
    from runner.history.service import HistoryService

    service = HistoryService()
    service.insert_run(record)
    runs = service.get_all_runs()
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session

from runner.db.engine import engine
from runner.db.models import (
    RunRecordCreate,
    InvocationRecordCreate,
    AuditScoreRecordCreate,
    PostIterationRecordCreate,
)
from runner.content.repository import (
    RunRecordRepository,
    InvocationRecordRepository,
    AuditScoreRecordRepository,
    PostIterationRecordRepository,
)
from runner.history.models import (
    RunRecord as LegacyRunRecord,
    InvocationRecord as LegacyInvocationRecord,
    AuditScoreRecord as LegacyAuditScoreRecord,
    PostIterationRecord as LegacyPostIterationRecord,
)


class HistoryService:
    """SQLModel-based history service.

    Provides backward-compatible API with HistoryDatabase while using
    PostgreSQL via SQLModel under the hood.
    """

    def __init__(self, user_id: Optional[UUID] = None):
        """Initialize history service.

        Args:
            user_id: Default user ID for operations. If not provided,
                     must be passed to methods that require it.
        """
        self._user_id = user_id

    def _get_session(self) -> Session:
        """Get a new database session."""
        return Session(engine)

    # ==========================================================================
    # RUNS
    # ==========================================================================

    def insert_run(self, record: LegacyRunRecord) -> None:
        """Insert new run record."""
        if not self._user_id:
            raise ValueError("user_id required for insert_run")

        with self._get_session() as session:
            repo = RunRecordRepository(session)
            create_data = RunRecordCreate(
                user_id=self._user_id,
                run_id=record.run_id,
                story=record.story,
                started_at=record.started_at,
                completed_at=record.completed_at,
                status=record.status or "running",
                duration_s=record.duration_s,
                total_tokens=record.total_tokens or 0,
                total_cost_usd=record.total_cost_usd or 0.0,
                final_post_path=record.final_post_path,
                final_score=record.final_score,
            )
            repo.create(create_data)

    def update_run_complete(
        self,
        run_id: str,
        completed_at: datetime,
        status: str,
        duration_s: float,
        total_tokens: int,
        total_cost_usd: float,
        final_post_path: Optional[str] = None,
        final_score: Optional[float] = None,
    ) -> None:
        """Update run with completion data."""
        with self._get_session() as session:
            repo = RunRecordRepository(session)
            repo.update_complete(
                run_id=run_id,
                completed_at=completed_at,
                status=status,
                duration_s=duration_s,
                total_tokens=total_tokens,
                total_cost_usd=total_cost_usd,
                final_post_path=final_post_path,
                final_score=final_score,
            )

    def get_run(self, run_id: str) -> Optional[LegacyRunRecord]:
        """Get run by ID."""
        with self._get_session() as session:
            repo = RunRecordRepository(session)
            record = repo.get_by_run_id(run_id)
            if not record:
                return None
            return self._to_legacy_run_record(record)

    def get_all_runs(self, limit: int = 100) -> list[LegacyRunRecord]:
        """Get all runs, most recent first."""
        if not self._user_id:
            raise ValueError("user_id required for get_all_runs")

        with self._get_session() as session:
            repo = RunRecordRepository(session)
            records = repo.list_by_user(self._user_id, limit=limit)
            return [self._to_legacy_run_record(r) for r in records]

    def _to_legacy_run_record(self, record) -> LegacyRunRecord:
        """Convert SQLModel record to legacy format."""
        return LegacyRunRecord(
            run_id=record.run_id,
            story=record.story,
            started_at=record.started_at,
            completed_at=record.completed_at,
            status=record.status,
            duration_s=record.duration_s,
            total_tokens=record.total_tokens,
            total_cost_usd=record.total_cost_usd,
            final_post_path=record.final_post_path,
            final_score=record.final_score,
        )

    # ==========================================================================
    # INVOCATIONS
    # ==========================================================================

    def insert_invocation(self, record: LegacyInvocationRecord) -> int:
        """Insert invocation record. Returns 0 (legacy returned SQLite ID)."""
        with self._get_session() as session:
            repo = InvocationRecordRepository(session)
            create_data = InvocationRecordCreate(
                run_id=record.run_id,
                agent=record.agent,
                state=record.state,
                persona=record.persona,
                started_at=record.started_at,
                duration_s=record.duration_s,
                success=record.success,
                input_tokens=record.input_tokens or 0,
                output_tokens=record.output_tokens or 0,
                total_tokens=record.total_tokens or 0,
                cost_usd=record.cost_usd or 0.0,
                output_word_count=record.output_word_count,
            )
            repo.create(create_data)
            return 0  # Legacy API returned auto-increment ID

    def get_invocations_for_run(self, run_id: str) -> list[LegacyInvocationRecord]:
        """Get all invocations for a run."""
        with self._get_session() as session:
            repo = InvocationRecordRepository(session)
            records = repo.list_by_run(run_id)
            return [self._to_legacy_invocation_record(r) for r in records]

    def _to_legacy_invocation_record(self, record) -> LegacyInvocationRecord:
        """Convert SQLModel record to legacy format."""
        return LegacyInvocationRecord(
            run_id=record.run_id,
            agent=record.agent,
            state=record.state,
            persona=record.persona,
            started_at=record.started_at,
            duration_s=record.duration_s,
            success=record.success,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            total_tokens=record.total_tokens,
            cost_usd=record.cost_usd,
            output_word_count=record.output_word_count,
        )

    # ==========================================================================
    # AUDIT SCORES
    # ==========================================================================

    def insert_audit_score(self, record: LegacyAuditScoreRecord) -> int:
        """Insert audit score record. Returns 0 (legacy returned SQLite ID)."""
        with self._get_session() as session:
            repo = AuditScoreRecordRepository(session)
            create_data = AuditScoreRecordCreate(
                run_id=record.run_id,
                auditor_agent=record.auditor_agent,
                target_agent=record.target_agent,
                state=record.state,
                overall_score=record.overall_score,
                hook_score=record.hook_score,
                specifics_score=record.specifics_score,
                voice_score=record.voice_score,
                structure_score=record.structure_score,
                feedback=record.feedback,
            )
            repo.create(create_data)
            return 0  # Legacy API returned auto-increment ID

    def get_audit_scores_for_run(self, run_id: str) -> list[LegacyAuditScoreRecord]:
        """Get all audit scores for a run."""
        with self._get_session() as session:
            repo = AuditScoreRecordRepository(session)
            records = repo.list_by_run(run_id)
            return [self._to_legacy_audit_score_record(r) for r in records]

    def _to_legacy_audit_score_record(self, record) -> LegacyAuditScoreRecord:
        """Convert SQLModel record to legacy format."""
        return LegacyAuditScoreRecord(
            run_id=record.run_id,
            auditor_agent=record.auditor_agent,
            target_agent=record.target_agent,
            state=record.state,
            overall_score=record.overall_score,
            hook_score=record.hook_score,
            specifics_score=record.specifics_score,
            voice_score=record.voice_score,
            structure_score=record.structure_score,
            feedback=record.feedback,
        )

    # ==========================================================================
    # POST ITERATIONS
    # ==========================================================================

    def insert_post_iteration(self, record: LegacyPostIterationRecord) -> None:
        """Insert or update post iteration record."""
        with self._get_session() as session:
            repo = PostIterationRecordRepository(session)
            create_data = PostIterationRecordCreate(
                run_id=record.run_id,
                story=record.story,
                iteration=record.iteration,
                final_score=record.final_score,
                total_cost_usd=record.total_cost_usd,
                improvements=record.improvements,
            )
            repo.upsert(create_data)

    def get_post_iterations(self, story: str) -> list[LegacyPostIterationRecord]:
        """Get all iterations for a story."""
        with self._get_session() as session:
            repo = PostIterationRecordRepository(session)
            records = repo.list_by_story(story)
            return [self._to_legacy_post_iteration_record(r) for r in records]

    def get_next_iteration_number(self, story: str) -> int:
        """Get the next iteration number for a story."""
        with self._get_session() as session:
            repo = PostIterationRecordRepository(session)
            return repo.get_next_iteration_number(story)

    def _to_legacy_post_iteration_record(self, record) -> LegacyPostIterationRecord:
        """Convert SQLModel record to legacy format."""
        return LegacyPostIterationRecord(
            story=record.story,
            run_id=record.run_id,
            iteration=record.iteration,
            final_score=record.final_score,
            total_cost_usd=record.total_cost_usd,
            improvements=record.improvements,
        )

    # ==========================================================================
    # Compatibility methods
    # ==========================================================================

    def initialize(self) -> None:
        """No-op for compatibility. Tables are created via Alembic migrations."""
        pass

    def connect(self):
        """No-op for compatibility. Sessions are managed per-operation."""
        pass

    def close(self) -> None:
        """No-op for compatibility. Sessions are managed per-operation."""
        pass
