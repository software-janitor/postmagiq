"""Shared fixtures for integration tests."""

import asyncio
import importlib
import pytest
from httpx import ASGITransport, AsyncClient
from typing import Any

from sqlmodel import Session, SQLModel

from api.main import app
from api.services.content_service import ContentService
from api.services.voice_service import VoiceService
from api.services.onboarding_service import OnboardingService
from api.routes import content, voice, onboarding, platforms
from runner.db import models  # noqa: F401
from runner.db.models import User, Goal, Chapter, Post

from tests.db_utils import create_test_engine, drop_test_schema

db_engine = importlib.import_module("runner.db.engine")


class SyncClient:
    """Synchronous wrapper around httpx AsyncClient for testing."""

    def __init__(self, app):
        self.app = app
        self.transport = ASGITransport(app=app)
        self.base_url = "http://testserver"

    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        """Make async request."""
        async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
            response = await client.request(method, url, **kwargs)
            return response

    def get(self, url: str, **kwargs):
        return self._run_async(self._request("GET", url, **kwargs))

    def post(self, url: str, **kwargs):
        return self._run_async(self._request("POST", url, **kwargs))

    def put(self, url: str, **kwargs):
        return self._run_async(self._request("PUT", url, **kwargs))

    def delete(self, url: str, **kwargs):
        return self._run_async(self._request("DELETE", url, **kwargs))

    def patch(self, url: str, **kwargs):
        return self._run_async(self._request("PATCH", url, **kwargs))


@pytest.fixture
def test_engine(monkeypatch):
    """Create and configure a test database engine."""
    engine, schema_name, database_url = create_test_engine()
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db_engine, "engine", engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    drop_test_schema(database_url, schema_name)


@pytest.fixture
def seeded_user(test_engine):
    """Seed the test database with core content data."""
    with Session(test_engine) as session:
        user = User(full_name="Test User", email="test@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        goal = Goal(
            user_id=user.id,
            positioning="Senior Engineer",
            signature_thesis="Test thesis",
            target_audience="Engineers",
            content_style="teaching",
            onboarding_mode="quick",
        )
        session.add(goal)
        session.commit()

        chapters = []
        for i in range(1, 4):
            chapter = Chapter(
                user_id=user.id,
                chapter_number=i,
                title=f"Chapter {i}",
                description=f"Description for chapter {i}",
                theme=f"Theme {i}",
                theme_description=f"Theme description {i}",
                weeks_start=(i - 1) * 4 + 1,
                weeks_end=i * 4,
            )
            session.add(chapter)
            session.commit()
            session.refresh(chapter)
            chapters.append(chapter)

        post_specs = [
            (chapters[0], "published"),
            (chapters[0], "ready"),
            (chapters[0], "draft"),
            (chapters[1], "needs_story"),
            (chapters[1], "not_started"),
            (chapters[2], "not_started"),
        ]
        for i, (chapter, status) in enumerate(post_specs, start=1):
            post = Post(
                user_id=user.id,
                chapter_id=chapter.id,
                post_number=i,
                topic=f"Post {i} topic",
                shape="FULL" if i % 2 == 0 else "PARTIAL",
                cadence="Teaching" if i % 2 == 0 else "Field Note",
                status=status,
            )
            session.add(post)
        session.commit()

    return user


@pytest.fixture
def test_content_service(test_engine):
    """ContentService using test database."""
    return ContentService()


@pytest.fixture
def seeded_content_service(seeded_user):
    """ContentService with seeded test database."""
    return ContentService()


@pytest.fixture
def test_voice_service(test_engine):
    """VoiceService using test database."""
    return VoiceService(content_service=ContentService())


@pytest.fixture
def client(test_engine, monkeypatch):
    """SyncClient with test database injected."""
    test_content_service = ContentService()
    test_voice_service = VoiceService(content_service=test_content_service)
    test_onboarding_service = OnboardingService(content_service=test_content_service)

    monkeypatch.setattr(content, "content_service", test_content_service)
    monkeypatch.setattr(voice, "voice_service", test_voice_service)
    monkeypatch.setattr(onboarding, "content_service", test_content_service)
    monkeypatch.setattr(onboarding, "onboarding_service", test_onboarding_service)
    monkeypatch.setattr(platforms, "content_service", test_content_service)

    return SyncClient(app)


@pytest.fixture
def seeded_client(seeded_user, monkeypatch):
    """SyncClient with seeded test database."""
    test_content_service = ContentService()
    test_voice_service = VoiceService(content_service=test_content_service)
    test_onboarding_service = OnboardingService(content_service=test_content_service)

    monkeypatch.setattr(content, "content_service", test_content_service)
    monkeypatch.setattr(voice, "voice_service", test_voice_service)
    monkeypatch.setattr(onboarding, "content_service", test_content_service)
    monkeypatch.setattr(onboarding, "onboarding_service", test_onboarding_service)
    monkeypatch.setattr(platforms, "content_service", test_content_service)

    return SyncClient(app)
