"""Unit tests for SQLModel repositories.

These tests run against PostgreSQL using a per-test schema.
They test the repository layer with the production database backend.

Note: These tests require sqlmodel to be installed.
Run with: pytest tests/unit/test_repositories.py -v
"""

import pytest
from datetime import datetime
from uuid import uuid4

# Skip all tests if sqlmodel is not installed
pytest.importorskip("sqlmodel")

from sqlmodel import Session, SQLModel

from runner.db.models import (
    User, UserCreate,
    Platform, PlatformCreate,
    Goal, GoalCreate,
    Chapter, ChapterCreate,
    Post, PostCreate,
    WritingSample, WritingSampleCreate,
    VoiceProfile, VoiceProfileCreate,
    WorkflowRun, WorkflowRunCreate,
    WorkflowPersona, WorkflowPersonaCreate,
)
from runner.content.repository import (
    UserRepository,
    PlatformRepository,
    GoalRepository,
    ChapterRepository,
    PostRepository,
    WritingSampleRepository,
    VoiceProfileRepository,
    WorkflowRunRepository,
    WorkflowPersonaRepository,
)
from tests.db_utils import create_test_engine, drop_test_schema, requires_db

pytestmark = requires_db  # Skip all tests in this module if DB not available


@pytest.fixture
def engine():
    """Create a PostgreSQL engine for testing."""
    engine, schema_name, database_url = create_test_engine()
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    drop_test_schema(database_url, schema_name)


@pytest.fixture
def session(engine):
    """Create a test session."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user(session):
    """Create a test user."""
    repo = UserRepository(session)
    user = repo.create(UserCreate(full_name="Test User", email="test@example.com"))
    return user


# =============================================================================
# UserRepository Tests
# =============================================================================

class TestUserRepository:
    """Tests for UserRepository."""

    def test_create_user(self, session):
        """Test creating a user."""
        repo = UserRepository(session)
        user = repo.create(UserCreate(full_name="Alice", email="alice@example.com"))

        assert user.id is not None
        assert user.full_name == "Alice"
        assert user.email == "alice@example.com"
        assert user.created_at is not None

    def test_get_user(self, session, test_user):
        """Test getting a user by ID."""
        repo = UserRepository(session)
        user = repo.get(test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.name == test_user.name

    def test_get_user_not_found(self, session):
        """Test getting a non-existent user."""
        repo = UserRepository(session)
        user = repo.get(uuid4())

        assert user is None

    def test_get_by_email(self, session, test_user):
        """Test getting a user by email."""
        repo = UserRepository(session)
        user = repo.get_by_email("test@example.com")

        assert user is not None
        assert user.id == test_user.id

    def test_list_all_users(self, session):
        """Test listing all users."""
        repo = UserRepository(session)
        repo.create(UserCreate(full_name="User 1", email="user1@example.com"))
        repo.create(UserCreate(full_name="User 2", email="user2@example.com"))

        users = repo.list_all()
        assert len(users) == 2

    def test_delete_user(self, session, test_user):
        """Test deleting a user."""
        repo = UserRepository(session)
        result = repo.delete(test_user.id)

        assert result is True
        assert repo.get(test_user.id) is None


# =============================================================================
# PlatformRepository Tests
# =============================================================================

class TestPlatformRepository:
    """Tests for PlatformRepository."""

    def test_create_platform(self, session, test_user):
        """Test creating a platform."""
        repo = PlatformRepository(session)
        platform = repo.create(PlatformCreate(
            user_id=test_user.id,
            name="LinkedIn",
            description="Professional network",
        ))

        assert platform.id is not None
        assert platform.name == "LinkedIn"
        assert platform.user_id == test_user.id

    def test_list_by_user(self, session, test_user):
        """Test listing platforms by user."""
        repo = PlatformRepository(session)
        repo.create(PlatformCreate(user_id=test_user.id, name="LinkedIn"))
        repo.create(PlatformCreate(user_id=test_user.id, name="Twitter"))

        platforms = repo.list_by_user(test_user.id)
        assert len(platforms) == 2

    def test_list_active(self, session, test_user):
        """Test listing active platforms."""
        repo = PlatformRepository(session)
        repo.create(PlatformCreate(user_id=test_user.id, name="Active", is_active=True))
        repo.create(PlatformCreate(user_id=test_user.id, name="Inactive", is_active=False))

        active = repo.list_active(test_user.id)
        assert len(active) == 1
        assert active[0].name == "Active"


# =============================================================================
# ChapterRepository Tests
# =============================================================================

class TestChapterRepository:
    """Tests for ChapterRepository."""

    def test_create_chapter(self, session, test_user):
        """Test creating a chapter."""
        repo = ChapterRepository(session)
        chapter = repo.create(ChapterCreate(
            user_id=test_user.id,
            chapter_number=1,
            title="Introduction",
        ))

        assert chapter.id is not None
        assert chapter.chapter_number == 1
        assert chapter.title == "Introduction"

    def test_list_by_user_ordered(self, session, test_user):
        """Test listing chapters returns them in order."""
        repo = ChapterRepository(session)
        repo.create(ChapterCreate(user_id=test_user.id, chapter_number=3, title="Three"))
        repo.create(ChapterCreate(user_id=test_user.id, chapter_number=1, title="One"))
        repo.create(ChapterCreate(user_id=test_user.id, chapter_number=2, title="Two"))

        chapters = repo.list_by_user(test_user.id)
        assert len(chapters) == 3
        assert chapters[0].chapter_number == 1
        assert chapters[1].chapter_number == 2
        assert chapters[2].chapter_number == 3

    def test_get_by_number(self, session, test_user):
        """Test getting chapter by number."""
        repo = ChapterRepository(session)
        repo.create(ChapterCreate(user_id=test_user.id, chapter_number=5, title="Five"))

        chapter = repo.get_by_number(test_user.id, 5)
        assert chapter is not None
        assert chapter.title == "Five"


# =============================================================================
# PostRepository Tests
# =============================================================================

class TestPostRepository:
    """Tests for PostRepository."""

    @pytest.fixture
    def test_chapter(self, session, test_user):
        """Create a test chapter."""
        repo = ChapterRepository(session)
        return repo.create(ChapterCreate(
            user_id=test_user.id,
            chapter_number=1,
            title="Test Chapter",
        ))

    def test_create_post(self, session, test_user, test_chapter):
        """Test creating a post."""
        repo = PostRepository(session)
        post = repo.create(PostCreate(
            user_id=test_user.id,
            chapter_id=test_chapter.id,
            post_number=1,
            topic="Test Topic",
        ))

        assert post.id is not None
        assert post.post_number == 1
        assert post.topic == "Test Topic"
        assert post.status == "not_started"

    def test_list_by_status(self, session, test_user, test_chapter):
        """Test listing posts by status."""
        repo = PostRepository(session)
        repo.create(PostCreate(
            user_id=test_user.id,
            chapter_id=test_chapter.id,
            post_number=1,
            status="draft",
        ))
        repo.create(PostCreate(
            user_id=test_user.id,
            chapter_id=test_chapter.id,
            post_number=2,
            status="published",
        ))

        drafts = repo.list_by_status(test_user.id, "draft")
        assert len(drafts) == 1
        assert drafts[0].post_number == 1

    def test_update_status(self, session, test_user, test_chapter):
        """Test updating post status."""
        repo = PostRepository(session)
        post = repo.create(PostCreate(
            user_id=test_user.id,
            chapter_id=test_chapter.id,
            post_number=1,
        ))

        updated = repo.update_status(post.id, "ready")
        assert updated is not None
        assert updated.status == "ready"


# =============================================================================
# VoiceProfileRepository Tests
# =============================================================================

class TestVoiceProfileRepository:
    """Tests for VoiceProfileRepository."""

    def test_create_voice_profile(self, session, test_user):
        """Test creating a voice profile."""
        repo = VoiceProfileRepository(session)
        profile = repo.create(VoiceProfileCreate(
            name="Professional Voice",
            slug="professional-voice",
            tone_description="Formal and confident",
        ))

        assert profile.id is not None
        assert profile.name == "Professional Voice"
        assert profile.slug == "professional-voice"

    def test_get_by_slug(self, session, test_user):
        """Test getting voice profile by slug."""
        repo = VoiceProfileRepository(session)
        repo.create(VoiceProfileCreate(
            name="Casual Voice",
            slug="casual-voice",
            tone_description="Relaxed and friendly",
        ))

        profile = repo.get_by_slug("casual-voice")
        assert profile is not None
        assert profile.name == "Casual Voice"


# =============================================================================
# WorkflowRunRepository Tests
# =============================================================================

class TestWorkflowRunRepository:
    """Tests for WorkflowRunRepository."""

    def test_create_workflow_run(self, session, test_user):
        """Test creating a workflow run."""
        repo = WorkflowRunRepository(session)
        run = repo.create(WorkflowRunCreate(
            user_id=test_user.id,
            run_id="2026-01-15_123456_post01",
            story="post_01",
        ))

        assert run.id is not None
        assert run.run_id == "2026-01-15_123456_post01"
        assert run.status == "running"

    def test_get_by_run_id(self, session, test_user):
        """Test getting workflow run by run_id."""
        repo = WorkflowRunRepository(session)
        repo.create(WorkflowRunCreate(
            user_id=test_user.id,
            run_id="unique-run-id",
            story="post_01",
        ))

        run = repo.get_by_run_id("unique-run-id")
        assert run is not None
        assert run.story == "post_01"

    def test_list_by_status(self, session, test_user):
        """Test listing runs by status."""
        repo = WorkflowRunRepository(session)
        repo.create(WorkflowRunCreate(
            user_id=test_user.id,
            run_id="run-1",
            story="post_01",
        ))

        running = repo.list_by_status(test_user.id, "running")
        assert len(running) == 1


# =============================================================================
# WorkflowPersonaRepository Tests
# =============================================================================

class TestWorkflowPersonaRepository:
    """Tests for WorkflowPersonaRepository."""

    def test_create_persona(self, session, test_user):
        """Test creating a workflow persona."""
        repo = WorkflowPersonaRepository(session)
        persona = repo.create(WorkflowPersonaCreate(
            user_id=test_user.id,
            name="Writer",
            slug="writer",
            content="You are a professional writer...",
        ))

        assert persona.id is not None
        assert persona.slug == "writer"

    def test_get_by_slug(self, session, test_user):
        """Test getting persona by slug."""
        repo = WorkflowPersonaRepository(session)
        repo.create(WorkflowPersonaCreate(
            user_id=test_user.id,
            name="Auditor",
            slug="auditor",
            content="You are a quality auditor...",
        ))

        persona = repo.get_by_slug(test_user.id, "auditor")
        assert persona is not None
        assert persona.name == "Auditor"

    def test_list_system_personas(self, session, test_user):
        """Test listing system personas."""
        repo = WorkflowPersonaRepository(session)
        repo.create(WorkflowPersonaCreate(
            user_id=test_user.id,
            name="System Writer",
            slug="system-writer",
            content="System prompt",
            is_system=True,
        ))
        repo.create(WorkflowPersonaCreate(
            user_id=test_user.id,
            name="User Writer",
            slug="user-writer",
            content="User prompt",
            is_system=False,
        ))

        system = repo.list_system_personas()
        assert len(system) == 1
        assert system[0].name == "System Writer"
