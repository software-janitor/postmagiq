"""Workspace context middleware.

Extracts workspace_id from URL path and verifies user membership.
Injects workspace and membership into request.state for downstream use.
"""

import re
from typing import Optional
from uuid import UUID

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from runner.db.models import Workspace, WorkspaceMembership, InviteStatus


# Regex pattern to extract workspace_id from URL
# Matches: /api/v1/w/{workspace_id}/...
WORKSPACE_URL_PATTERN = re.compile(r"^/api/v\d+/w/([a-f0-9-]{36})/")


class WorkspaceMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and validate workspace context from URL.

    For routes matching /api/v1/w/{workspace_id}/..., this middleware:
    1. Extracts workspace_id from the URL path
    2. Verifies the authenticated user is a member of the workspace
    3. Loads the workspace and membership objects
    4. Injects them into request.state for use by route handlers

    Routes not matching the workspace pattern are passed through unchanged.

    Requires AuthMiddleware to run first to set request.state.user.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract workspace_id from URL if present
        workspace_id = self._extract_workspace_id(request.url.path)

        if workspace_id is None:
            # Not a workspace-scoped route, pass through
            return await call_next(request)

        # Require authentication for workspace routes
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for workspace access",
            )

        # Load workspace and verify membership
        workspace, membership = await self._load_workspace_context(
            workspace_id, user.id
        )

        # Inject into request state
        request.state.workspace = workspace
        request.state.membership = membership
        request.state.workspace_id = workspace_id

        return await call_next(request)

    def _extract_workspace_id(self, path: str) -> Optional[UUID]:
        """Extract workspace_id from URL path.

        Args:
            path: Request URL path

        Returns:
            UUID if path matches workspace pattern, None otherwise
        """
        match = WORKSPACE_URL_PATTERN.match(path)
        if not match:
            return None

        try:
            return UUID(match.group(1))
        except ValueError:
            return None

    async def _load_workspace_context(
        self, workspace_id: UUID, user_id: UUID
    ) -> tuple[Workspace, WorkspaceMembership]:
        """Load workspace and verify user membership.

        Args:
            workspace_id: The workspace to access
            user_id: The authenticated user

        Returns:
            Tuple of (Workspace, WorkspaceMembership)

        Raises:
            HTTPException 404: Workspace not found
            HTTPException 403: User is not a member
        """
        from runner.db.engine import engine
        from sqlmodel import Session, select

        with Session(engine) as session:
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
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.invite_status == InviteStatus.accepted,
            )
            membership = session.exec(statement).first()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a member of this workspace",
                )

            # Detach from session for use outside
            session.expunge(workspace)
            session.expunge(membership)

            return workspace, membership


def get_workspace_from_request(request: Request) -> Workspace:
    """Helper to get workspace from request state.

    Use in route handlers when workspace context is required.

    Raises:
        HTTPException 500: Workspace not set (middleware not applied)
    """
    workspace = getattr(request.state, "workspace", None)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workspace context not available",
        )
    return workspace


def get_membership_from_request(request: Request) -> WorkspaceMembership:
    """Helper to get membership from request state.

    Use in route handlers when membership context is required.

    Raises:
        HTTPException 500: Membership not set (middleware not applied)
    """
    membership = getattr(request.state, "membership", None)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Membership context not available",
        )
    return membership
