"""Shared fixtures for integration tests."""

import asyncio
import importlib
import os
import pytest
from httpx import ASGITransport, AsyncClient
from typing import Any

from sqlmodel import Session, SQLModel

# Skip API imports if JWT_SECRET not set (for standalone agent tests)
if os.environ.get("JWT_SECRET"):
    from api.main import app
else:
    app = None

from runner.db import models  # noqa: F401
from runner.db.models.user import User

from tests.db_utils import create_test_engine, drop_test_schema, is_database_available

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
    """Seed the test database with a test user."""
    with Session(test_engine) as session:
        user = User(full_name="Test User", email="test@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@pytest.fixture
def client(test_engine):
    """SyncClient with test database injected."""
    if app is None:
        pytest.skip("JWT_SECRET not set - API not available")
    return SyncClient(app)


@pytest.fixture
def seeded_client(seeded_user):
    """SyncClient with seeded test database."""
    if app is None:
        pytest.skip("JWT_SECRET not set - API not available")
    return SyncClient(app)
