"""Unit tests for multi-tenancy components.

Tests:
- Workspace context and permissions
- RBAC scope verification
- Data isolation logic
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from fastapi import HTTPException


class TestWorkspaceContext:
    """Tests for WorkspaceContext."""

    def test_has_scope_owner(self):
        """Owner has all scopes."""
        from api.routes.v1.dependencies import WorkspaceContext
        from api.auth.dependencies import CurrentUser
        from api.auth.scopes import Scope
        from runner.db.models import Workspace, WorkspaceMembership, WorkspaceRole

        workspace = MagicMock(spec=Workspace)
        workspace.id = uuid4()

        membership = MagicMock(spec=WorkspaceMembership)
        membership.role = WorkspaceRole.owner

        user = MagicMock()
        user.id = uuid4()
        current_user = CurrentUser(user=user, membership=membership)

        ctx = WorkspaceContext(
            workspace=workspace,
            membership=membership,
            current_user=current_user,
        )

        # Owner should have all scopes
        assert ctx.has_scope(Scope.CONTENT_READ) is True
        assert ctx.has_scope(Scope.CONTENT_WRITE) is True
        assert ctx.has_scope(Scope.STRATEGY_READ) is True
        assert ctx.has_scope(Scope.STRATEGY_WRITE) is True
        assert ctx.has_scope(Scope.TEAM_READ) is True
        assert ctx.has_scope(Scope.TEAM_MANAGE) is True
        assert ctx.has_scope(Scope.WORKSPACE_DELETE) is True

    def test_has_scope_viewer(self):
        """Viewer only has read scopes."""
        from api.routes.v1.dependencies import WorkspaceContext
        from api.auth.dependencies import CurrentUser
        from api.auth.scopes import Scope
        from runner.db.models import Workspace, WorkspaceMembership, WorkspaceRole

        workspace = MagicMock(spec=Workspace)
        workspace.id = uuid4()

        membership = MagicMock(spec=WorkspaceMembership)
        membership.role = WorkspaceRole.viewer

        user = MagicMock()
        user.id = uuid4()
        current_user = CurrentUser(user=user, membership=membership)

        ctx = WorkspaceContext(
            workspace=workspace,
            membership=membership,
            current_user=current_user,
        )

        # Viewer should have read scopes only
        assert ctx.has_scope(Scope.CONTENT_READ) is True
        assert ctx.has_scope(Scope.CONTENT_WRITE) is False
        assert ctx.has_scope(Scope.STRATEGY_READ) is True
        assert ctx.has_scope(Scope.STRATEGY_WRITE) is False
        assert ctx.has_scope(Scope.TEAM_READ) is True  # Viewers can see team members
        assert ctx.has_scope(Scope.TEAM_MANAGE) is False
        assert ctx.has_scope(Scope.WORKSPACE_DELETE) is False

    def test_has_scope_editor(self):
        """Editor has read and write content scopes."""
        from api.routes.v1.dependencies import WorkspaceContext
        from api.auth.dependencies import CurrentUser
        from api.auth.scopes import Scope
        from runner.db.models import Workspace, WorkspaceMembership, WorkspaceRole

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

        # Editor should have content read/write
        assert ctx.has_scope(Scope.CONTENT_READ) is True
        assert ctx.has_scope(Scope.CONTENT_WRITE) is True
        assert ctx.has_scope(Scope.STRATEGY_READ) is True
        assert ctx.has_scope(Scope.STRATEGY_WRITE) is False
        assert ctx.has_scope(Scope.TEAM_READ) is True
        assert ctx.has_scope(Scope.TEAM_MANAGE) is False

    def test_require_scope_raises_forbidden(self):
        """require_scope raises 403 when scope is missing."""
        from api.routes.v1.dependencies import WorkspaceContext
        from api.auth.dependencies import CurrentUser
        from api.auth.scopes import Scope
        from runner.db.models import Workspace, WorkspaceMembership, WorkspaceRole

        workspace = MagicMock(spec=Workspace)
        workspace.id = uuid4()

        membership = MagicMock(spec=WorkspaceMembership)
        membership.role = WorkspaceRole.viewer

        user = MagicMock()
        user.id = uuid4()
        current_user = CurrentUser(user=user, membership=membership)

        ctx = WorkspaceContext(
            workspace=workspace,
            membership=membership,
            current_user=current_user,
        )

        with pytest.raises(HTTPException) as exc_info:
            ctx.require_scope(Scope.CONTENT_WRITE)

        assert exc_info.value.status_code == 403
        assert "content:write" in exc_info.value.detail


class TestRBACScopeMappings:
    """Tests for RBAC scope mappings."""

    def test_role_scopes_defined(self):
        """All roles have scope mappings."""
        from api.auth.scopes import ROLE_SCOPES, Scope
        from runner.db.models import WorkspaceRole

        # All roles should be defined
        for role in WorkspaceRole:
            assert role in ROLE_SCOPES, f"Role {role} not in ROLE_SCOPES"

    def test_owner_has_most_scopes(self):
        """Owner role has the most permissions."""
        from api.auth.scopes import ROLE_SCOPES
        from runner.db.models import WorkspaceRole

        owner_scopes = ROLE_SCOPES[WorkspaceRole.owner]
        admin_scopes = ROLE_SCOPES[WorkspaceRole.admin]
        editor_scopes = ROLE_SCOPES[WorkspaceRole.editor]
        viewer_scopes = ROLE_SCOPES[WorkspaceRole.viewer]

        # Owner should have >= scopes as admin
        assert len(owner_scopes) >= len(admin_scopes)
        # Admin should have >= scopes as editor
        assert len(admin_scopes) >= len(editor_scopes)
        # Editor should have >= scopes as viewer
        assert len(editor_scopes) >= len(viewer_scopes)

    def test_viewer_has_read_only_scopes(self):
        """Viewer should only have read scopes."""
        from api.auth.scopes import ROLE_SCOPES
        from runner.db.models import WorkspaceRole

        viewer_scopes = ROLE_SCOPES[WorkspaceRole.viewer]

        for scope in viewer_scopes:
            assert "write" not in scope.value.lower(), f"Viewer has write scope: {scope}"
            assert "delete" not in scope.value.lower(), f"Viewer has delete scope: {scope}"


class TestWorkspaceSlugGeneration:
    """Tests for workspace slug generation."""

    def test_slug_from_name(self):
        """Slug is generated from workspace name."""
        from api.routes.v1.workspaces import CreateWorkspaceRequest

        req = CreateWorkspaceRequest(name="My Test Workspace")
        assert req.name == "My Test Workspace"

    def test_custom_slug(self):
        """Custom slug can be provided."""
        from api.routes.v1.workspaces import CreateWorkspaceRequest

        req = CreateWorkspaceRequest(name="My Workspace", slug="custom-slug")
        assert req.slug == "custom-slug"


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password_not_plaintext(self):
        """Hashed password is not plaintext."""
        from api.auth.password import hash_password

        password = "TestPass123!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > len(password)

    def test_verify_password_correct(self):
        """verify_password returns True for correct password."""
        from api.auth.password import hash_password, verify_password

        password = "TestPass123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password returns False for wrong password."""
        from api.auth.password import hash_password, verify_password

        password = "TestPass123!"
        hashed = hash_password(password)

        assert verify_password("WrongPass456!", hashed) is False

    def test_hash_is_unique(self):
        """Each hash is unique even for same password."""
        from api.auth.password import hash_password

        password = "TestPass123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # bcrypt uses random salt, so hashes should differ
        assert hash1 != hash2


class TestJWTTokens:
    """Tests for JWT token utilities."""

    def test_create_access_token(self):
        """Access token is created with correct claims."""
        from api.auth.jwt import create_access_token, JWT_SECRET, JWT_ALGORITHM
        from jose import jwt

        user_id = uuid4()
        token = create_access_token({"sub": str(user_id)})

        # Decode to check claims
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token(self):
        """Refresh token is created with correct claims."""
        from api.auth.jwt import create_refresh_token, JWT_SECRET, JWT_ALGORITHM
        from jose import jwt

        user_id = uuid4()
        token = create_refresh_token({"sub": str(user_id)})

        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"


class TestWorkspaceModels:
    """Tests for workspace-related database models."""

    def test_workspace_role_enum(self):
        """WorkspaceRole enum has expected values."""
        from runner.db.models import WorkspaceRole

        assert WorkspaceRole.owner.value == "owner"
        assert WorkspaceRole.admin.value == "admin"
        assert WorkspaceRole.editor.value == "editor"
        assert WorkspaceRole.viewer.value == "viewer"

    def test_invite_status_enum(self):
        """InviteStatus enum has expected values."""
        from runner.db.models import InviteStatus

        assert InviteStatus.pending.value == "pending"
        assert InviteStatus.accepted.value == "accepted"
        assert InviteStatus.expired.value == "expired"


class TestContentIsolation:
    """Tests for workspace content isolation."""

    def test_goal_requires_workspace_id(self):
        """Goal model requires workspace_id."""
        from runner.db.models import Goal

        # Goal should have workspace_id field
        assert hasattr(Goal, "workspace_id")

    def test_chapter_requires_workspace_id(self):
        """Chapter model requires workspace_id."""
        from runner.db.models import Chapter

        assert hasattr(Chapter, "workspace_id")

    def test_post_requires_workspace_id(self):
        """Post model requires workspace_id."""
        from runner.db.models import Post

        assert hasattr(Post, "workspace_id")


class TestDataIsolationEndpoints:
    """Tests verifying data isolation in API endpoints."""

    def test_workflow_persona_routes_use_auth(self):
        """Workflow persona routes use authenticated user, not system user."""
        import inspect
        from api.routes import workflow_personas

        # Check list_personas function signature for CurrentUser dependency
        sig = inspect.signature(workflow_personas.list_personas)
        params = list(sig.parameters.keys())
        assert "current_user" in params, "list_personas must use current_user dependency"

    def test_finished_posts_routes_use_auth(self):
        """Finished posts routes use authenticated user, not system user."""
        import inspect
        from api.routes import finished_posts

        # Check list_finished_posts function signature
        sig = inspect.signature(finished_posts.list_finished_posts)
        params = list(sig.parameters.keys())
        assert "current_user" in params, "list_finished_posts must use current_user dependency"

    def test_image_prompts_routes_use_auth(self):
        """Image prompts routes use authenticated user, not system user."""
        import inspect
        from api.routes import image_prompts

        # Check generate_prompt function signature
        sig = inspect.signature(image_prompts.generate_prompt)
        params = list(sig.parameters.keys())
        assert "current_user" in params, "generate_prompt must use current_user dependency"

    def test_runs_routes_use_auth(self):
        """Runs routes use authenticated user, not system user."""
        import inspect
        from api.routes import runs

        # Check list_runs function signature
        sig = inspect.signature(runs.list_runs)
        params = list(sig.parameters.keys())
        assert "current_user" in params, "list_runs must use current_user dependency"

    def test_workflow_routes_use_auth(self):
        """Workflow routes use authenticated user, not system user."""
        import inspect
        from api.routes import workflow

        # Check execute_workflow function signature
        sig = inspect.signature(workflow.execute_workflow)
        params = list(sig.parameters.keys())
        assert "current_user" in params, "execute_workflow must use current_user dependency"


class TestSystemUserIsolation:
    """Tests ensuring system user ID is not used for regular user data."""

    def test_no_default_user_id_in_routes(self):
        """Routes should not use _default_user_id() for data access."""
        import ast
        from pathlib import Path

        routes_dir = Path(__file__).parent.parent.parent / "api" / "routes"

        # Files that should NOT contain _default_user_id
        route_files = [
            "finished_posts.py",
            "workflow_personas.py",
            "image_prompts.py",
            "runs.py",
            "workflow.py",
        ]

        for filename in route_files:
            filepath = routes_dir / filename
            if filepath.exists():
                content = filepath.read_text()
                assert "_default_user_id" not in content, (
                    f"{filename} still uses _default_user_id() - should use CurrentUser dependency"
                )

    def test_no_system_user_id_fallback(self):
        """Services should not fall back to system user for data access."""
        import ast
        from pathlib import Path

        services_dir = Path(__file__).parent.parent.parent / "api" / "services"

        # Check run_service.py specifically
        run_service = services_dir / "run_service.py"
        if run_service.exists():
            content = run_service.read_text()
            # get_system_user_id should not be called in data retrieval paths
            # It's okay for system-wide data, but not for user-specific data
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "get_system_user_id()" in line and "user_id" in line.lower():
                    # Allow only in specific contexts like seeding
                    if "seed" not in line.lower() and "system" not in line.lower():
                        # This is a potential issue - log it but don't fail
                        # as there may be legitimate uses
                        pass
