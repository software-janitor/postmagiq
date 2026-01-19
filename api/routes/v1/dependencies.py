"""Dependencies for workspace-scoped routes.

Provides FastAPI dependencies to:
- Extract workspace_id from URL path
- Verify user has access to workspace
- Inject workspace context into route handlers
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Path, status
from sqlmodel import Session, select

from api.auth.dependencies import CurrentUser, get_current_user
from api.auth.scopes import Scope
from runner.db.engine import get_session_dependency
from runner.db.models import (
    Workspace,
    WorkspaceMembership,
    InviteStatus,
)


class WorkspaceContext:
    """Container for workspace context in route handlers.

    Contains the workspace, user's membership, and current user.
    Provides helper methods for common operations.
    """

    def __init__(
        self,
        workspace: Workspace,
        membership: WorkspaceMembership,
        current_user: CurrentUser,
    ):
        self.workspace = workspace
        self.membership = membership
        self.current_user = current_user

    @property
    def workspace_id(self) -> UUID:
        return self.workspace.id

    @property
    def user_id(self) -> UUID:
        return self.current_user.user_id

    def has_scope(self, scope: Scope) -> bool:
        """Check if user has scope in this workspace."""
        from api.auth.scopes import has_scope
        return has_scope(self.membership.role, scope)

    def require_scope(self, scope: Scope) -> None:
        """Raise HTTPException if user lacks required scope."""
        if not self.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {scope.value}",
            )


async def get_workspace_context(
    workspace_id: Annotated[UUID, Path(description="Workspace UUID")],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> WorkspaceContext:
    """Get workspace context from URL path parameter.

    This dependency:
    1. Extracts workspace_id from the URL path
    2. Loads the workspace from the database
    3. Verifies the user is a member with accepted status
    4. Returns a WorkspaceContext with all relevant objects

    Usage:
        @router.get("/posts")
        async def list_posts(
            ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)]
        ):
            return get_posts_for_workspace(ctx.workspace_id)

    Args:
        workspace_id: UUID from URL path
        current_user: Authenticated user from JWT
        session: Database session

    Returns:
        WorkspaceContext with workspace, membership, and user

    Raises:
        HTTPException 404: Workspace not found
        HTTPException 403: User is not a member
    """
    # Load workspace
    workspace = session.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Load membership
    statement = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == current_user.user_id,
        WorkspaceMembership.invite_status == InviteStatus.accepted,
    )
    membership = session.exec(statement).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    # Update CurrentUser with membership context
    current_user_with_membership = CurrentUser(
        user=current_user.user,
        membership=membership,
    )

    return WorkspaceContext(
        workspace=workspace,
        membership=membership,
        current_user=current_user_with_membership,
    )


def require_workspace_scope(scope: Scope):
    """Create a dependency that requires a specific scope in the workspace.

    Usage:
        @router.post("/posts")
        async def create_post(
            ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))]
        ):
            ...

    Args:
        scope: Required permission scope

    Returns:
        Dependency that returns WorkspaceContext if authorized
    """

    async def scope_checker(
        ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    ) -> WorkspaceContext:
        ctx.require_scope(scope)
        return ctx

    return scope_checker


# Type aliases for cleaner route signatures
WorkspaceCtx = Annotated[WorkspaceContext, Depends(get_workspace_context)]
