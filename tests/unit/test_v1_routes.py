"""Tests for v1 workspace-scoped API routes."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException


class TestWorkspaceContext:
    """Tests for WorkspaceContext dependency."""

    def test_workspace_context_has_scope(self):
        """WorkspaceContext.has_scope delegates to scopes module."""
        from api.routes.v1.dependencies import WorkspaceContext
        from api.auth.dependencies import CurrentUser
        from runner.db.models import Workspace, WorkspaceMembership, WorkspaceRole, InviteStatus

        # Create mock objects
        workspace = MagicMock(spec=Workspace)
        workspace.id = uuid4()

        membership = MagicMock(spec=WorkspaceMembership)
        membership.role = WorkspaceRole.editor

        user = MagicMock()
        user.id = uuid4()
        current_user = CurrentUser(user=user, membership=membership)

        ctx = WorkspaceContext(
            workspace=workspace,
            membership=membership,
            current_user=current_user,
        )

        # Editor should have content:read scope
        from api.auth.scopes import Scope
        assert ctx.has_scope(Scope.CONTENT_READ) is True

        # Editor should not have workspace:delete scope
        assert ctx.has_scope(Scope.WORKSPACE_DELETE) is False

    def test_workspace_context_require_scope_raises(self):
        """WorkspaceContext.require_scope raises HTTPException when scope missing."""
        from api.routes.v1.dependencies import WorkspaceContext
        from api.auth.dependencies import CurrentUser
        from api.auth.scopes import Scope
        from runner.db.models import Workspace, WorkspaceMembership, WorkspaceRole

        workspace = MagicMock(spec=Workspace)
        workspace.id = uuid4()

        membership = MagicMock(spec=WorkspaceMembership)
        membership.role = WorkspaceRole.viewer  # Viewer has limited permissions

        user = MagicMock()
        user.id = uuid4()
        current_user = CurrentUser(user=user, membership=membership)

        ctx = WorkspaceContext(
            workspace=workspace,
            membership=membership,
            current_user=current_user,
        )

        # Viewer should not have content:write scope
        with pytest.raises(HTTPException) as exc_info:
            ctx.require_scope(Scope.CONTENT_WRITE)

        assert exc_info.value.status_code == 403
        assert "content:write" in exc_info.value.detail


class TestWorkspaceRoutes:
    """Tests for workspace management routes."""

    def test_create_workspace_request_model(self):
        """CreateWorkspaceRequest validates input."""
        from api.routes.v1.workspaces import CreateWorkspaceRequest

        # Valid request
        req = CreateWorkspaceRequest(name="My Workspace")
        assert req.name == "My Workspace"
        assert req.slug is None
        assert req.description is None

        # With optional fields
        req = CreateWorkspaceRequest(
            name="My Workspace",
            slug="my-workspace",
            description="Test description",
        )
        assert req.slug == "my-workspace"
        assert req.description == "Test description"

    def test_create_workspace_request_validation(self):
        """CreateWorkspaceRequest rejects invalid input."""
        from api.routes.v1.workspaces import CreateWorkspaceRequest
        from pydantic import ValidationError

        # Empty name should fail
        with pytest.raises(ValidationError):
            CreateWorkspaceRequest(name="")

        # Name too long should fail
        with pytest.raises(ValidationError):
            CreateWorkspaceRequest(name="x" * 101)

    def test_invite_member_request_model(self):
        """InviteMemberRequest validates input."""
        from api.routes.v1.workspaces import InviteMemberRequest
        from runner.db.models import WorkspaceRole

        # Valid request with default role
        req = InviteMemberRequest(email="test@example.com")
        assert req.email == "test@example.com"
        assert req.role == WorkspaceRole.editor

        # With explicit role
        req = InviteMemberRequest(email="admin@example.com", role=WorkspaceRole.admin)
        assert req.role == WorkspaceRole.admin

    def test_invite_member_request_email_validation(self):
        """InviteMemberRequest rejects invalid email."""
        from api.routes.v1.workspaces import InviteMemberRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            InviteMemberRequest(email="not-an-email")


class TestWorkspaceContentRoutes:
    """Tests for workspace-scoped content routes."""

    def test_goal_response_model(self):
        """GoalResponse model structure."""
        from api.routes.v1.workspace_content import GoalResponse
        from uuid import uuid4

        goal_id = uuid4()
        workspace_id = uuid4()

        response = GoalResponse(
            id=goal_id,
            workspace_id=workspace_id,
            positioning="Tech Lead",
            signature_thesis="AI needs systems",
            target_audience="Engineers",
            content_style="Reflective",
            strategy_type="series",
            voice_profile_id=None,
            image_config_set_id=None,
        )

        assert response.id == goal_id
        assert response.workspace_id == workspace_id
        assert response.strategy_type == "series"

    def test_create_goal_request_defaults(self):
        """CreateGoalRequest has correct defaults."""
        from api.routes.v1.workspace_content import CreateGoalRequest

        req = CreateGoalRequest()
        assert req.strategy_type == "series"
        assert req.positioning is None
        assert req.signature_thesis is None

    def test_post_response_model(self):
        """PostResponse model structure."""
        from api.routes.v1.workspace_content import PostResponse
        from uuid import uuid4

        post_id = uuid4()
        workspace_id = uuid4()
        chapter_id = uuid4()

        response = PostResponse(
            id=post_id,
            workspace_id=workspace_id,
            chapter_id=chapter_id,
            post_number=1,
            topic="AI adoption",
            shape="FULL",
            cadence="Teaching",
            entry_point="In Media Res",
            status="draft",
            guidance=None,
            story_used=None,
            published_url=None,
        )

        assert response.id == post_id
        assert response.post_number == 1
        assert response.status == "draft"

    def test_update_post_request_partial(self):
        """UpdatePostRequest allows partial updates."""
        from api.routes.v1.workspace_content import UpdatePostRequest

        # Only update status
        req = UpdatePostRequest(status="ready")
        data = req.model_dump(exclude_unset=True)

        assert data == {"status": "ready"}
        assert "topic" not in data

    def test_chapter_response_includes_counts(self):
        """ChapterResponse includes post counts."""
        from api.routes.v1.workspace_content import ChapterResponse
        from uuid import uuid4

        response = ChapterResponse(
            id=uuid4(),
            workspace_id=uuid4(),
            chapter_number=1,
            title="Chapter 1",
            description=None,
            theme="Tool-first AI adoption",
            theme_description=None,
            weeks_start=1,
            weeks_end=6,
            post_count=6,
            completed_count=2,
        )

        assert response.post_count == 6
        assert response.completed_count == 2


class TestRBACIntegration:
    """Tests for RBAC scope enforcement."""

    def test_role_scope_mapping_exists(self):
        """Verify ROLE_SCOPES mapping is defined."""
        from api.auth.scopes import ROLE_SCOPES, Scope
        from runner.db.models import WorkspaceRole

        # All roles should have scopes defined
        assert WorkspaceRole.owner in ROLE_SCOPES
        assert WorkspaceRole.admin in ROLE_SCOPES
        assert WorkspaceRole.editor in ROLE_SCOPES
        assert WorkspaceRole.viewer in ROLE_SCOPES

        # Owner should have all scopes
        owner_scopes = ROLE_SCOPES[WorkspaceRole.owner]
        assert Scope.WORKSPACE_DELETE in owner_scopes
        assert Scope.CONTENT_WRITE in owner_scopes

        # Viewer should have limited scopes
        viewer_scopes = ROLE_SCOPES[WorkspaceRole.viewer]
        assert Scope.CONTENT_READ in viewer_scopes
        assert Scope.CONTENT_WRITE not in viewer_scopes

    def test_has_scope_function(self):
        """Test has_scope helper function."""
        from api.auth.scopes import has_scope, Scope
        from runner.db.models import WorkspaceRole

        # Owner has everything
        assert has_scope(WorkspaceRole.owner, Scope.WORKSPACE_DELETE) is True

        # Viewer is read-only
        assert has_scope(WorkspaceRole.viewer, Scope.CONTENT_READ) is True
        assert has_scope(WorkspaceRole.viewer, Scope.CONTENT_WRITE) is False

        # Editor can write content but not settings
        assert has_scope(WorkspaceRole.editor, Scope.CONTENT_WRITE) is True
        assert has_scope(WorkspaceRole.editor, Scope.WORKSPACE_SETTINGS) is False
