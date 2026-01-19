"""Integration tests for client portal API endpoints."""

import os
import pytest
from datetime import datetime
from uuid import uuid4, UUID

# Use in-memory SQLite for fast integration tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlmodel import Session, SQLModel, create_engine, select
from httpx import ASGITransport, AsyncClient
import asyncio

from runner.db.models import (
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
    InviteStatus,
    Post,
    Chapter,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStage,
    WhitelabelConfig,
)
from api.auth.password import hash_password
from api.auth.jwt import create_access_token


# =============================================================================
# Test Database Setup
# =============================================================================


def create_test_engine():
    """Create a fresh SQLite engine for testing.

    Uses shared cache mode for in-memory database to allow multiple connections
    to see the same data.
    """
    return create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )


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

    async def _request(self, method: str, url: str, **kwargs):
        """Make async request."""
        async with AsyncClient(transport=self.transport, base_url=self.base_url) as client:
            response = await client.request(method, url, **kwargs)
            return response

    def get(self, url: str, **kwargs):
        return self._run_async(self._request("GET", url, **kwargs))

    def post(self, url: str, **kwargs):
        return self._run_async(self._request("POST", url, **kwargs))


@pytest.fixture(scope="function")
def test_engine():
    """Create and configure a test database engine."""
    engine = create_test_engine()
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def test_client(test_engine):
    """Create test client with overridden session dependency."""
    from api.main import app
    from runner.db.engine import get_session_dependency

    def override_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session_dependency] = override_session
    client = SyncClient(app)
    yield client
    app.dependency_overrides.clear()


# =============================================================================
# Data Fixtures
# =============================================================================


@pytest.fixture
def test_workspace(test_session):
    """Create a test workspace with whitelabel config."""
    workspace = Workspace(
        name="Test Agency",
        slug="test-agency",
        owner_id=uuid4(),  # Temporary, will be updated
    )
    test_session.add(workspace)
    test_session.commit()
    test_session.refresh(workspace)

    # Add whitelabel config
    whitelabel = WhitelabelConfig(
        workspace_id=workspace.id,
        company_name="Branded Agency",
        primary_color="#FF5733",
        portal_welcome_text="Welcome to the review portal",
        is_active=True,
    )
    test_session.add(whitelabel)
    test_session.commit()

    return workspace


@pytest.fixture
def test_user(test_session, test_workspace):
    """Create a test user with workspace membership."""
    user = User(
        name="Test Client",
        email="client@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=True,
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)

    # Update workspace owner
    test_workspace.owner_id = user.id
    test_session.add(test_workspace)

    # Add membership
    membership = WorkspaceMembership(
        workspace_id=test_workspace.id,
        user_id=user.id,
        email=user.email,
        role=WorkspaceRole.viewer,
        invite_status=InviteStatus.accepted,
    )
    test_session.add(membership)
    test_session.commit()

    return user


@pytest.fixture
def portal_token(test_user, test_workspace):
    """Create a portal access token."""
    token_data = {
        "sub": str(test_user.id),
        "workspace_id": str(test_workspace.id),
        "email": test_user.email,
        "role": "viewer",
    }
    return create_access_token(token_data, token_type="portal_access")


@pytest.fixture
def test_chapter(test_session, test_workspace, test_user):
    """Create a test chapter."""
    chapter = Chapter(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        chapter_number=1,
        title="Test Chapter",
    )
    test_session.add(chapter)
    test_session.commit()
    test_session.refresh(chapter)
    return chapter


@pytest.fixture
def test_posts(test_session, test_workspace, test_user, test_chapter):
    """Create test posts in reviewable statuses."""
    posts = []
    statuses = ["pending_approval", "ready", "changes_requested", "draft"]

    for i, status in enumerate(statuses):
        post = Post(
            user_id=test_user.id,
            workspace_id=test_workspace.id,
            chapter_id=test_chapter.id,
            post_number=i + 1,
            topic=f"Test Topic {i + 1}",
            status=status,
        )
        test_session.add(post)
        test_session.commit()
        test_session.refresh(post)
        posts.append(post)

    return posts


@pytest.fixture
def test_approval_stage(test_session, test_workspace, test_user):
    """Create a test approval stage."""
    stage = ApprovalStage(
        workspace_id=test_workspace.id,
        created_by_id=test_user.id,
        name="Client Review",
        order=1,
        is_required=True,
        is_active=True,
    )
    test_session.add(stage)
    test_session.commit()
    test_session.refresh(stage)
    return stage


@pytest.fixture
def test_posts_with_approval(
    test_session, test_workspace, test_user, test_chapter, test_approval_stage
):
    """Create test posts with pending approval requests."""
    posts = []

    for i in range(2):
        post = Post(
            user_id=test_user.id,
            workspace_id=test_workspace.id,
            chapter_id=test_chapter.id,
            post_number=i + 10,
            topic=f"Post for Review {i + 1}",
            status="pending_approval",
        )
        test_session.add(post)
        test_session.commit()
        test_session.refresh(post)

        # Create approval request
        approval = ApprovalRequest(
            post_id=post.id,
            workspace_id=test_workspace.id,
            stage_id=test_approval_stage.id,
            submitted_by_id=test_user.id,
            status=ApprovalStatus.PENDING.value,
        )
        test_session.add(approval)
        test_session.commit()
        test_session.refresh(approval)

        posts.append({"post": post, "approval": approval})

    return posts


# =============================================================================
# Tests
# =============================================================================


class TestPortalBranding:
    """Tests for portal branding/login page endpoints."""

    def test_get_login_page_returns_branding(self, test_client, test_workspace):
        """GET /portal/login/{workspace_id} returns workspace branding."""
        response = test_client.get(f"/api/portal/login/{test_workspace.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_name"] == "Test Agency"
        assert data["company_name"] == "Branded Agency"
        assert data["primary_color"] == "#FF5733"
        assert data["portal_welcome_text"] == "Welcome to the review portal"

    def test_get_login_page_workspace_not_found(self, test_client):
        """GET /portal/login/{workspace_id} returns 404 for missing workspace."""
        fake_id = uuid4()
        response = test_client.get(f"/api/portal/login/{fake_id}")
        assert response.status_code == 404
        # Check either format (depends on error handler setup)
        data = response.json()
        if "error" in data:
            assert data["error"]["message"] == "Workspace not found"
        else:
            assert data["detail"] == "Workspace not found"


class TestPortalLogin:
    """Tests for portal authentication endpoints."""

    def test_login_success(self, test_client, test_workspace, test_user):
        """POST /portal/login authenticates user and returns token."""
        response = test_client.post(
            "/api/portal/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
                "workspace_id": str(test_workspace.id),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email
        assert "branding" in data

    def test_login_invalid_password(self, test_client, test_workspace, test_user):
        """POST /portal/login fails with wrong password."""
        response = test_client.post(
            "/api/portal/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
                "workspace_id": str(test_workspace.id),
            },
        )
        assert response.status_code == 401
        data = response.json()
        msg = data.get("error", {}).get("message") or data.get("detail", "")
        assert "Invalid credentials" in msg

    def test_login_user_not_member(self, test_client, test_workspace, test_session):
        """POST /portal/login fails if user not member of workspace."""
        # Create a user who is NOT a member of the workspace
        non_member = User(
            name="Non Member",
            email="nonmember@example.com",
            password_hash=hash_password("testpassword123"),
            is_active=True,
        )
        test_session.add(non_member)
        test_session.commit()

        response = test_client.post(
            "/api/portal/login",
            json={
                "email": "nonmember@example.com",
                "password": "testpassword123",
                "workspace_id": str(test_workspace.id),
            },
        )
        assert response.status_code == 401


class TestPortalPosts:
    """Tests for portal post listing and detail endpoints."""

    def test_list_posts_requires_auth(self, test_client):
        """GET /portal/posts requires authentication."""
        response = test_client.get("/api/portal/posts")
        assert response.status_code == 401

    def test_list_posts_returns_reviewable_posts(
        self, test_client, portal_token, test_posts
    ):
        """GET /portal/posts returns posts in review statuses."""
        response = test_client.get(
            "/api/portal/posts",
            headers={"Authorization": f"Bearer {portal_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
        assert "total" in data
        # Should return posts in pending_approval, ready, changes_requested (3)
        # Not draft (1)
        assert data["total"] == 3

    def test_list_posts_with_status_filter(
        self, test_client, portal_token, test_posts
    ):
        """GET /portal/posts?status_filter=pending_approval filters posts."""
        response = test_client.get(
            "/api/portal/posts?status_filter=pending_approval",
            headers={"Authorization": f"Bearer {portal_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        for post in data["posts"]:
            assert post["status"] == "pending_approval"

    def test_get_post_detail(self, test_client, portal_token, test_posts):
        """GET /portal/posts/{post_id} returns post detail."""
        post_id = test_posts[0].id
        response = test_client.get(
            f"/api/portal/posts/{post_id}",
            headers={"Authorization": f"Bearer {portal_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(post_id)
        assert "topic" in data
        assert "status" in data

    def test_get_post_detail_not_found(self, test_client, portal_token):
        """GET /portal/posts/{post_id} returns 404 for missing post."""
        fake_id = uuid4()
        response = test_client.get(
            f"/api/portal/posts/{fake_id}",
            headers={"Authorization": f"Bearer {portal_token}"},
        )
        assert response.status_code == 404


class TestPortalApproval:
    """Tests for portal approval/rejection endpoints."""

    def test_approve_post_success(
        self, test_client, portal_token, test_posts_with_approval
    ):
        """POST /portal/posts/{post_id}/approve approves the post."""
        post_id = test_posts_with_approval[0]["post"].id
        response = test_client.post(
            f"/api/portal/posts/{post_id}/approve",
            headers={"Authorization": f"Bearer {portal_token}"},
            json={"notes": "Looks great!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "approved"
        assert data["message"] == "Post approved successfully"

    def test_approve_post_no_pending_request(
        self, test_client, portal_token, test_posts
    ):
        """POST /portal/posts/{post_id}/approve fails if no pending request."""
        # test_posts don't have approval requests
        post_id = test_posts[0].id
        response = test_client.post(
            f"/api/portal/posts/{post_id}/approve",
            headers={"Authorization": f"Bearer {portal_token}"},
        )
        assert response.status_code == 400
        data = response.json()
        msg = data.get("error", {}).get("message") or data.get("detail", "")
        assert "No pending approval request" in msg

    def test_reject_post_success(
        self, test_client, portal_token, test_posts_with_approval
    ):
        """POST /portal/posts/{post_id}/reject rejects the post with feedback."""
        post_id = test_posts_with_approval[0]["post"].id
        response = test_client.post(
            f"/api/portal/posts/{post_id}/reject",
            headers={"Authorization": f"Bearer {portal_token}"},
            json={"feedback": "Please revise the introduction"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "rejected"
        assert data["message"] == "Post rejected with feedback"

    def test_reject_post_requires_feedback(
        self, test_client, portal_token, test_posts_with_approval
    ):
        """POST /portal/posts/{post_id}/reject requires feedback."""
        post_id = test_posts_with_approval[0]["post"].id
        response = test_client.post(
            f"/api/portal/posts/{post_id}/reject",
            headers={"Authorization": f"Bearer {portal_token}"},
            json={"feedback": ""},
        )
        # Validation errors can return 400 or 422
        assert response.status_code in [400, 422]

    def test_approve_post_not_found(self, test_client, portal_token):
        """POST /portal/posts/{post_id}/approve returns 404 for missing post."""
        fake_id = uuid4()
        response = test_client.post(
            f"/api/portal/posts/{fake_id}/approve",
            headers={"Authorization": f"Bearer {portal_token}"},
        )
        assert response.status_code == 404


class TestPortalTokenValidation:
    """Tests for portal token validation."""

    def test_regular_token_rejected(self, test_client, test_user):
        """Regular access tokens (not portal_access type) are rejected."""
        # Create a regular token (type="access" not "portal_access")
        token_data = {"sub": str(test_user.id)}
        regular_token = create_access_token(token_data, token_type="access")

        response = test_client.get(
            "/api/portal/posts",
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert response.status_code == 401
        data = response.json()
        msg = data.get("error", {}).get("message") or data.get("detail", "")
        assert "Invalid token type for portal access" in msg
