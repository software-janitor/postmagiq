"""SQLModel-based repository layer for content queries.

This module provides repository classes that encapsulate database queries
using SQLModel. Each repository handles a specific domain entity.

Usage:
    from runner.db import get_session
    from runner.content.repository import UserRepository

    with get_session() as session:
        repo = UserRepository(session)
        user = repo.get(user_id)
        users = repo.list_all()
"""

from typing import Optional, TypeVar, Generic
from uuid import UUID

from sqlmodel import Session, select

from runner.db.models import (
    # Core
    User, UserCreate,
    Platform, PlatformCreate,
    Goal, GoalCreate,
    Chapter, ChapterCreate,
    Post, PostCreate,
    # Voice
    WritingSample, WritingSampleCreate,
    VoiceProfile, VoiceProfileCreate,
    # Workflow
    WorkflowRun, WorkflowRunCreate,
    WorkflowOutput, WorkflowOutputCreate,
    WorkflowPersona, WorkflowPersonaCreate,
    WorkflowSession, WorkflowSessionCreate,
    WorkflowStateMetric, WorkflowStateMetricCreate,
    # History
    RunRecord, RunRecordCreate,
    InvocationRecord, InvocationRecordCreate,
    AuditScoreRecord, AuditScoreRecordCreate,
    PostIterationRecord, PostIterationRecordCreate,
)

T = TypeVar("T")
CreateT = TypeVar("CreateT")


# =============================================================================
# Base Repository
# =============================================================================

class BaseRepository(Generic[T, CreateT]):
    """Base repository with common CRUD operations."""

    model: type[T]

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: CreateT) -> T:
        """Create a new record."""
        obj = self.model.model_validate(data)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def get(self, id: UUID) -> Optional[T]:
        """Get a record by ID."""
        return self.session.get(self.model, id)

    def list_all(self, workspace_id: Optional[UUID] = None) -> list[T]:
        """List all records, optionally filtered by workspace.

        Args:
            workspace_id: If provided, filter by workspace. If None, returns all records
                         (for backward compatibility with legacy/CLI usage).
        """
        statement = select(self.model)
        # Filter by workspace_id if model has the attribute and workspace_id is provided
        if workspace_id is not None and hasattr(self.model, "workspace_id"):
            statement = statement.where(self.model.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def delete(self, id: UUID) -> bool:
        """Delete a record by ID. Returns True if deleted."""
        obj = self.get(id)
        if obj:
            self.session.delete(obj)
            self.session.commit()
            return True
        return False


# =============================================================================
# User Repository
# =============================================================================

class UserRepository(BaseRepository[User, UserCreate]):
    """Repository for User operations."""

    model = User

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()


# =============================================================================
# Platform Repository
# =============================================================================

class PlatformRepository(BaseRepository[Platform, PlatformCreate]):
    """Repository for Platform operations."""

    model = Platform

    def list_by_user(self, user_id: UUID, workspace_id: Optional[UUID] = None) -> list[Platform]:
        """List all platforms for a user, optionally filtered by workspace."""
        statement = select(Platform).where(Platform.user_id == user_id)
        if workspace_id is not None:
            statement = statement.where(Platform.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_active(self, user_id: UUID, workspace_id: Optional[UUID] = None) -> list[Platform]:
        """List active platforms for a user, optionally filtered by workspace."""
        statement = select(Platform).where(
            Platform.user_id == user_id,
            Platform.is_active == True
        )
        if workspace_id is not None:
            statement = statement.where(Platform.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())


# =============================================================================
# Goal Repository
# =============================================================================

class GoalRepository(BaseRepository[Goal, GoalCreate]):
    """Repository for Goal operations."""

    model = Goal

    def get_by_user(self, user_id: UUID, workspace_id: Optional[UUID] = None) -> Optional[Goal]:
        """Get the goal for a user, optionally filtered by workspace."""
        statement = select(Goal).where(Goal.user_id == user_id)
        if workspace_id is not None:
            statement = statement.where(Goal.workspace_id == workspace_id)
        return self.session.exec(statement).first()

    def get_by_platform(self, user_id: UUID, platform_id: UUID, workspace_id: Optional[UUID] = None) -> Optional[Goal]:
        """Get the goal for a specific user and platform, optionally filtered by workspace."""
        statement = select(Goal).where(
            Goal.user_id == user_id,
            Goal.platform_id == platform_id
        )
        if workspace_id is not None:
            statement = statement.where(Goal.workspace_id == workspace_id)
        return self.session.exec(statement).first()

    def get_by_workspace(self, workspace_id: UUID) -> Optional[Goal]:
        """Get the goal for a workspace (assumes one goal per workspace for now)."""
        statement = select(Goal).where(Goal.workspace_id == workspace_id)
        return self.session.exec(statement).first()

    def list_by_user(self, user_id: UUID, workspace_id: Optional[UUID] = None) -> list[Goal]:
        """List all goals for a user, optionally filtered by workspace."""
        statement = select(Goal).where(Goal.user_id == user_id)
        if workspace_id is not None:
            statement = statement.where(Goal.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())


# =============================================================================
# Chapter Repository
# =============================================================================

class ChapterRepository(BaseRepository[Chapter, ChapterCreate]):
    """Repository for Chapter operations."""

    model = Chapter

    def list_by_user(self, user_id: UUID, workspace_id: Optional[UUID] = None) -> list[Chapter]:
        """List all chapters for a user, optionally filtered by workspace."""
        statement = select(Chapter).where(Chapter.user_id == user_id).order_by(Chapter.chapter_number)
        if workspace_id is not None:
            statement = statement.where(Chapter.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_by_platform(self, user_id: UUID, platform_id: UUID, workspace_id: Optional[UUID] = None) -> list[Chapter]:
        """List chapters for a specific platform, optionally filtered by workspace."""
        statement = select(Chapter).where(
            Chapter.user_id == user_id,
            Chapter.platform_id == platform_id
        ).order_by(Chapter.chapter_number)
        if workspace_id is not None:
            statement = statement.where(Chapter.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_by_workspace(self, workspace_id: UUID) -> list[Chapter]:
        """List all chapters for a workspace."""
        statement = select(Chapter).where(Chapter.workspace_id == workspace_id).order_by(Chapter.chapter_number)
        return list(self.session.exec(statement).all())

    def get_by_number(self, user_id: UUID, chapter_number: int, platform_id: Optional[UUID] = None, workspace_id: Optional[UUID] = None) -> Optional[Chapter]:
        """Get a chapter by number, optionally filtered by platform and/or workspace."""
        statement = select(Chapter).where(
            Chapter.user_id == user_id,
            Chapter.chapter_number == chapter_number
        )
        if platform_id is not None:
            statement = statement.where(Chapter.platform_id == platform_id)
        if workspace_id is not None:
            statement = statement.where(Chapter.workspace_id == workspace_id)
        return self.session.exec(statement).first()


# =============================================================================
# Post Repository
# =============================================================================

class PostRepository(BaseRepository[Post, PostCreate]):
    """Repository for Post operations."""

    model = Post

    def list_by_user(self, user_id: UUID, workspace_id: Optional[UUID] = None) -> list[Post]:
        """List all posts for a user, optionally filtered by workspace."""
        statement = select(Post).where(Post.user_id == user_id).order_by(Post.post_number)
        if workspace_id is not None:
            statement = statement.where(Post.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_by_chapter(self, chapter_id: UUID, workspace_id: Optional[UUID] = None) -> list[Post]:
        """List posts for a specific chapter, optionally filtered by workspace."""
        statement = select(Post).where(Post.chapter_id == chapter_id).order_by(Post.post_number)
        if workspace_id is not None:
            statement = statement.where(Post.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_by_workspace(self, workspace_id: UUID) -> list[Post]:
        """List all posts for a workspace."""
        statement = select(Post).where(Post.workspace_id == workspace_id).order_by(Post.post_number)
        return list(self.session.exec(statement).all())

    def list_by_status(self, user_id: UUID, status: str, workspace_id: Optional[UUID] = None) -> list[Post]:
        """List posts with a specific status, optionally filtered by workspace."""
        statement = select(Post).where(
            Post.user_id == user_id,
            Post.status == status
        ).order_by(Post.post_number)
        if workspace_id is not None:
            statement = statement.where(Post.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def get_by_number(self, user_id: UUID, post_number: int, workspace_id: Optional[UUID] = None) -> Optional[Post]:
        """Get a post by number, optionally filtered by workspace."""
        statement = select(Post).where(
            Post.user_id == user_id,
            Post.post_number == post_number
        )
        if workspace_id is not None:
            statement = statement.where(Post.workspace_id == workspace_id)
        return self.session.exec(statement).first()

    def update_status(self, post_id: UUID, status: str) -> Optional[Post]:
        """Update post status."""
        post = self.get(post_id)
        if post:
            post.status = status
            self.session.add(post)
            self.session.commit()
            self.session.refresh(post)
        return post


# =============================================================================
# Voice Repositories
# =============================================================================

class WritingSampleRepository(BaseRepository[WritingSample, WritingSampleCreate]):
    """Repository for WritingSample operations."""

    model = WritingSample

    def list_by_user(self, user_id: UUID, workspace_id: Optional[UUID] = None) -> list[WritingSample]:
        """List all writing samples for a user, optionally filtered by workspace."""
        statement = select(WritingSample).where(WritingSample.user_id == user_id)
        if workspace_id is not None:
            statement = statement.where(WritingSample.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_by_workspace(self, workspace_id: UUID) -> list[WritingSample]:
        """List all writing samples for a workspace."""
        statement = select(WritingSample).where(WritingSample.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())


class VoiceProfileRepository(BaseRepository[VoiceProfile, VoiceProfileCreate]):
    """Repository for VoiceProfile operations."""

    model = VoiceProfile

    def get_by_slug(self, slug: str, workspace_id: Optional[UUID] = None) -> Optional[VoiceProfile]:
        """Get a voice profile by slug, optionally within a workspace."""
        if workspace_id:
            statement = select(VoiceProfile).where(
                VoiceProfile.slug == slug,
                VoiceProfile.workspace_id == workspace_id
            )
        else:
            statement = select(VoiceProfile).where(
                VoiceProfile.slug == slug,
                VoiceProfile.workspace_id == None
            )
        return self.session.exec(statement).first()

    def list_by_workspace(self, workspace_id: UUID) -> list[VoiceProfile]:
        """List voice profiles for a workspace."""
        statement = select(VoiceProfile).where(VoiceProfile.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_presets(self) -> list[VoiceProfile]:
        """List system preset voice profiles (workspace_id is None, is_preset is True)."""
        statement = select(VoiceProfile).where(
            VoiceProfile.workspace_id == None,
            VoiceProfile.is_preset == True
        )
        return list(self.session.exec(statement).all())


# =============================================================================
# Workflow Repositories
# =============================================================================

class WorkflowRunRepository(BaseRepository[WorkflowRun, WorkflowRunCreate]):
    """Repository for WorkflowRun operations."""

    model = WorkflowRun

    def get_by_run_id(self, run_id: str) -> Optional[WorkflowRun]:
        """Get a workflow run by its run_id string."""
        statement = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
        return self.session.exec(statement).first()

    def list_by_user(self, user_id: UUID, limit: int = 50, workspace_id: Optional[UUID] = None) -> list[WorkflowRun]:
        """List recent workflow runs for a user, optionally filtered by workspace."""
        statement = select(WorkflowRun).where(
            WorkflowRun.user_id == user_id
        ).order_by(WorkflowRun.started_at.desc()).limit(limit)
        if workspace_id is not None:
            statement = statement.where(WorkflowRun.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_by_workspace(self, workspace_id: UUID, limit: int = 50) -> list[WorkflowRun]:
        """List recent workflow runs for a workspace."""
        statement = select(WorkflowRun).where(
            WorkflowRun.workspace_id == workspace_id
        ).order_by(WorkflowRun.started_at.desc()).limit(limit)
        return list(self.session.exec(statement).all())

    def get_latest_by_story(
        self,
        user_id: UUID,
        story: str,
        workspace_id: Optional[UUID] = None,
    ) -> Optional[WorkflowRun]:
        """Get the latest workflow run for a story."""
        statement = select(WorkflowRun).where(
            WorkflowRun.user_id == user_id,
            WorkflowRun.story == story,
        ).order_by(WorkflowRun.started_at.desc())
        if workspace_id is not None:
            statement = statement.where(WorkflowRun.workspace_id == workspace_id)
        return self.session.exec(statement).first()

    def get_latest_with_final_output(
        self,
        user_id: UUID,
        story: str,
        workspace_id: Optional[UUID] = None,
    ) -> Optional[WorkflowRun]:
        """Get the latest workflow run that has a 'final' output."""
        statement = (
            select(WorkflowRun)
            .join(WorkflowOutput, WorkflowRun.run_id == WorkflowOutput.run_id)
            .where(
                WorkflowRun.user_id == user_id,
                WorkflowRun.story == story,
                WorkflowOutput.output_type == "final",
            )
            .order_by(WorkflowRun.started_at.desc())
        )
        if workspace_id is not None:
            statement = statement.where(WorkflowRun.workspace_id == workspace_id)
        return self.session.exec(statement).first()

    def list_by_status(self, user_id: UUID, status: str, workspace_id: Optional[UUID] = None) -> list[WorkflowRun]:
        """List workflow runs by status, optionally filtered by workspace."""
        statement = select(WorkflowRun).where(
            WorkflowRun.user_id == user_id,
            WorkflowRun.status == status
        ).order_by(WorkflowRun.started_at.desc())
        if workspace_id is not None:
            statement = statement.where(WorkflowRun.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())


class WorkflowOutputRepository(BaseRepository[WorkflowOutput, WorkflowOutputCreate]):
    """Repository for WorkflowOutput operations."""

    model = WorkflowOutput

    def list_by_run(self, run_id: str) -> list[WorkflowOutput]:
        """List all outputs for a workflow run."""
        statement = select(WorkflowOutput).where(
            WorkflowOutput.run_id == run_id
        ).order_by(WorkflowOutput.created_at)
        return list(self.session.exec(statement).all())

    def list_by_type(self, run_id: str, output_type: str) -> list[WorkflowOutput]:
        """List all outputs for a workflow run by output type."""
        statement = select(WorkflowOutput).where(
            WorkflowOutput.run_id == run_id,
            WorkflowOutput.output_type == output_type,
        ).order_by(WorkflowOutput.created_at)
        return list(self.session.exec(statement).all())

    def get_latest_by_state(self, run_id: str, state_name: str) -> Optional[WorkflowOutput]:
        """Get the latest output for a specific state."""
        statement = select(WorkflowOutput).where(
            WorkflowOutput.run_id == run_id,
            WorkflowOutput.state_name == state_name
        ).order_by(WorkflowOutput.created_at.desc())
        return self.session.exec(statement).first()


class WorkflowPersonaRepository(BaseRepository[WorkflowPersona, WorkflowPersonaCreate]):
    """Repository for WorkflowPersona operations."""

    model = WorkflowPersona

    def get_by_slug(self, user_id: UUID, slug: str, workspace_id: Optional[UUID] = None) -> Optional[WorkflowPersona]:
        """Get a persona by slug, optionally filtered by workspace."""
        statement = select(WorkflowPersona).where(
            WorkflowPersona.user_id == user_id,
            WorkflowPersona.slug == slug
        )
        if workspace_id is not None:
            statement = statement.where(WorkflowPersona.workspace_id == workspace_id)
        return self.session.exec(statement).first()

    def list_by_user(self, user_id: UUID, workspace_id: Optional[UUID] = None) -> list[WorkflowPersona]:
        """List all personas for a user, optionally filtered by workspace."""
        statement = select(WorkflowPersona).where(WorkflowPersona.user_id == user_id)
        if workspace_id is not None:
            statement = statement.where(WorkflowPersona.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_by_workspace(self, workspace_id: UUID) -> list[WorkflowPersona]:
        """List all personas for a workspace."""
        statement = select(WorkflowPersona).where(WorkflowPersona.workspace_id == workspace_id)
        return list(self.session.exec(statement).all())

    def list_system_personas(self) -> list[WorkflowPersona]:
        """List system-wide personas."""
        statement = select(WorkflowPersona).where(WorkflowPersona.is_system == True)
        return list(self.session.exec(statement).all())


class WorkflowSessionRepository(BaseRepository[WorkflowSession, WorkflowSessionCreate]):
    """Repository for WorkflowSession operations."""

    model = WorkflowSession

    def get_by_agent(
        self,
        user_id: UUID,
        agent_name: str,
        run_id: Optional[str] = None,
    ) -> Optional[WorkflowSession]:
        """Get session by user, agent, and optional run."""
        statement = select(WorkflowSession).where(
            WorkflowSession.user_id == user_id,
            WorkflowSession.agent_name == agent_name,
        )
        if run_id is None:
            statement = statement.where(WorkflowSession.run_id == None)
        else:
            statement = statement.where(WorkflowSession.run_id == run_id)
        return self.session.exec(statement).first()

    def upsert_session(
        self,
        user_id: UUID,
        agent_name: str,
        session_id: str,
        run_id: Optional[str] = None,
    ) -> WorkflowSession:
        """Create or update a workflow session."""
        existing = self.get_by_agent(user_id, agent_name, run_id)
        if existing:
            existing.session_id = session_id
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        create_data = WorkflowSessionCreate(
            user_id=user_id,
            agent_name=agent_name,
            session_id=session_id,
            run_id=run_id,
        )
        return self.create(create_data)

    def delete_by_agent(
        self,
        user_id: UUID,
        agent_name: str,
        run_id: Optional[str] = None,
    ) -> bool:
        """Delete session by user, agent, and optional run."""
        existing = self.get_by_agent(user_id, agent_name, run_id)
        if not existing:
            return False
        self.session.delete(existing)
        self.session.commit()
        return True


class WorkflowStateMetricRepository(BaseRepository[WorkflowStateMetric, WorkflowStateMetricCreate]):
    """Repository for WorkflowStateMetric operations."""

    model = WorkflowStateMetric

    def list_by_run(self, run_id: str) -> list[WorkflowStateMetric]:
        """List all metrics for a run."""
        statement = (
            select(WorkflowStateMetric)
            .where(WorkflowStateMetric.run_id == run_id)
            .order_by(WorkflowStateMetric.created_at)
        )
        return list(self.session.exec(statement).all())


# =============================================================================
# History Repositories
# =============================================================================

class RunRecordRepository(BaseRepository[RunRecord, RunRecordCreate]):
    """Repository for RunRecord operations."""

    model = RunRecord

    def get_by_run_id(self, run_id: str) -> Optional[RunRecord]:
        """Get a run record by its run_id string."""
        statement = select(RunRecord).where(RunRecord.run_id == run_id)
        return self.session.exec(statement).first()

    def list_by_user(self, user_id: UUID, limit: int = 100) -> list[RunRecord]:
        """List run records for a user, most recent first."""
        statement = (
            select(RunRecord)
            .where(RunRecord.user_id == user_id)
            .order_by(RunRecord.started_at.desc())
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def list_by_story(self, story: str, user_id: UUID) -> list[RunRecord]:
        """List run records for a specific story."""
        statement = (
            select(RunRecord)
            .where(RunRecord.story == story, RunRecord.user_id == user_id)
            .order_by(RunRecord.started_at.desc())
        )
        return list(self.session.exec(statement).all())

    def list_by_status(self, status: str, user_id: UUID) -> list[RunRecord]:
        """List run records by status."""
        statement = (
            select(RunRecord)
            .where(RunRecord.status == status, RunRecord.user_id == user_id)
            .order_by(RunRecord.started_at.desc())
        )
        return list(self.session.exec(statement).all())

    def update_complete(
        self,
        run_id: str,
        completed_at,
        status: str,
        duration_s: float,
        total_tokens: int,
        total_cost_usd: float,
        final_post_path: Optional[str] = None,
        final_score: Optional[float] = None,
    ) -> Optional[RunRecord]:
        """Update run with completion data."""
        record = self.get_by_run_id(run_id)
        if record:
            record.completed_at = completed_at
            record.status = status
            record.duration_s = duration_s
            record.total_tokens = total_tokens
            record.total_cost_usd = total_cost_usd
            record.final_post_path = final_post_path
            record.final_score = final_score
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
        return record


class InvocationRecordRepository(BaseRepository[InvocationRecord, InvocationRecordCreate]):
    """Repository for InvocationRecord operations."""

    model = InvocationRecord

    def list_by_run(self, run_id: str) -> list[InvocationRecord]:
        """List all invocations for a run, ordered by start time."""
        statement = (
            select(InvocationRecord)
            .where(InvocationRecord.run_id == run_id)
            .order_by(InvocationRecord.started_at)
        )
        return list(self.session.exec(statement).all())

    def list_by_agent(self, agent: str, run_id: str) -> list[InvocationRecord]:
        """List invocations for a specific agent in a run."""
        statement = (
            select(InvocationRecord)
            .where(InvocationRecord.run_id == run_id, InvocationRecord.agent == agent)
            .order_by(InvocationRecord.started_at)
        )
        return list(self.session.exec(statement).all())


class AuditScoreRecordRepository(BaseRepository[AuditScoreRecord, AuditScoreRecordCreate]):
    """Repository for AuditScoreRecord operations."""

    model = AuditScoreRecord

    def list_by_run(self, run_id: str) -> list[AuditScoreRecord]:
        """List all audit scores for a run."""
        statement = select(AuditScoreRecord).where(AuditScoreRecord.run_id == run_id)
        return list(self.session.exec(statement).all())

    def list_by_auditor(self, auditor_agent: str, run_id: str) -> list[AuditScoreRecord]:
        """List audit scores from a specific auditor."""
        statement = (
            select(AuditScoreRecord)
            .where(
                AuditScoreRecord.run_id == run_id,
                AuditScoreRecord.auditor_agent == auditor_agent,
            )
        )
        return list(self.session.exec(statement).all())


class PostIterationRecordRepository(BaseRepository[PostIterationRecord, PostIterationRecordCreate]):
    """Repository for PostIterationRecord operations."""

    model = PostIterationRecord

    def list_by_story(self, story: str) -> list[PostIterationRecord]:
        """List all iterations for a story."""
        statement = (
            select(PostIterationRecord)
            .where(PostIterationRecord.story == story)
            .order_by(PostIterationRecord.iteration)
        )
        return list(self.session.exec(statement).all())

    def list_by_run(self, run_id: str) -> list[PostIterationRecord]:
        """List all iterations for a specific run."""
        statement = select(PostIterationRecord).where(PostIterationRecord.run_id == run_id)
        return list(self.session.exec(statement).all())

    def get_next_iteration_number(self, story: str) -> int:
        """Get the next iteration number for a story."""
        statement = (
            select(PostIterationRecord.iteration)
            .where(PostIterationRecord.story == story)
            .order_by(PostIterationRecord.iteration.desc())
            .limit(1)
        )
        result = self.session.exec(statement).first()
        return (result or 0) + 1

    def upsert(self, data: PostIterationRecordCreate) -> PostIterationRecord:
        """Insert or update a post iteration record."""
        # Check if exists
        statement = select(PostIterationRecord).where(
            PostIterationRecord.story == data.story,
            PostIterationRecord.run_id == data.run_id,
        )
        existing = self.session.exec(statement).first()

        if existing:
            existing.iteration = data.iteration
            existing.final_score = data.final_score
            existing.total_cost_usd = data.total_cost_usd
            existing.improvements = data.improvements
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            return self.create(data)
