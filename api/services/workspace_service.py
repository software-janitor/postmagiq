"""Service for workspace management operations.

Provides high-level operations for workspace CRUD, wrapping
repository operations with business logic and session management.
"""

import re
from typing import Optional
from uuid import UUID

from runner.db.engine import engine
from runner.db.models import (
    Workspace, WorkspaceCreate, WorkspaceRead,
    WorkspaceMembership, WorkspaceMembershipCreate,
    WorkspaceRole, InviteStatus,
)
from runner.content.workspace_repository import (
    WorkspaceRepository,
    WorkspaceMembershipRepository,
)
from sqlmodel import Session


def _generate_slug(name: str) -> str:
    """Generate a URL-safe slug from workspace name.

    Args:
        name: Workspace name

    Returns:
        Lowercase slug with special characters replaced by hyphens
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = name.lower().strip()
    # Remove special characters except hyphens
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    # Replace whitespace with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Trim hyphens from ends
    slug = slug.strip("-")
    return slug or "workspace"


class WorkspaceService:
    """Service for workspace management.

    Handles workspace CRUD operations including creating the owner
    membership when a workspace is created.
    """

    def create_workspace(
        self,
        owner_id: UUID,
        name: str,
        slug: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Workspace:
        """Create a new workspace with owner membership.

        Creates the workspace and automatically adds the owner as a member
        with the owner role and accepted status.

        Args:
            owner_id: User ID of the workspace owner
            name: Workspace display name
            slug: URL-safe identifier (auto-generated from name if not provided)
            description: Optional workspace description

        Returns:
            Created Workspace object

        Raises:
            ValueError: If slug is already taken
        """
        with Session(engine) as session:
            workspace_repo = WorkspaceRepository(session)
            membership_repo = WorkspaceMembershipRepository(session)

            # Generate slug if not provided
            if not slug:
                slug = _generate_slug(name)

            # Check if slug is already taken
            existing = workspace_repo.get_by_slug(slug)
            if existing:
                # Append a random suffix to make it unique
                import uuid
                slug = f"{slug}-{str(uuid.uuid4())[:8]}"

            # Create workspace
            workspace_data = WorkspaceCreate(
                name=name,
                slug=slug,
                description=description,
                owner_id=owner_id,
            )
            workspace = workspace_repo.create(workspace_data)

            # Get owner's email for the membership record
            from runner.db.models import User
            owner = session.get(User, owner_id)
            owner_email = owner.email if owner else f"user-{owner_id}@workspace.local"

            # Create owner membership (auto-accepted)
            membership_data = WorkspaceMembershipCreate(
                workspace_id=workspace.id,
                user_id=owner_id,
                email=owner_email,
                role=WorkspaceRole.owner,
            )
            membership = WorkspaceMembership.model_validate(membership_data)
            membership.invite_status = InviteStatus.accepted
            membership.accepted_at = membership.invited_at
            session.add(membership)
            session.commit()

            # Refresh workspace to ensure it's detached properly
            session.refresh(workspace)
            session.expunge(workspace)

            return workspace

    def get_workspace(self, workspace_id: UUID) -> Optional[Workspace]:
        """Get a workspace by ID.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workspace if found, None otherwise
        """
        with Session(engine) as session:
            workspace_repo = WorkspaceRepository(session)
            workspace = workspace_repo.get(workspace_id)
            if workspace:
                session.expunge(workspace)
            return workspace

    def get_workspace_by_slug(self, slug: str) -> Optional[Workspace]:
        """Get a workspace by slug.

        Args:
            slug: URL-safe workspace identifier

        Returns:
            Workspace if found, None otherwise
        """
        with Session(engine) as session:
            workspace_repo = WorkspaceRepository(session)
            workspace = workspace_repo.get_by_slug(slug)
            if workspace:
                session.expunge(workspace)
            return workspace

    def list_user_workspaces(self, user_id: UUID) -> list[Workspace]:
        """List all workspaces a user has access to.

        Returns workspaces where the user is a member with accepted status.

        Args:
            user_id: User UUID

        Returns:
            List of workspaces the user can access
        """
        with Session(engine) as session:
            workspace_repo = WorkspaceRepository(session)
            workspaces = workspace_repo.list_by_user(user_id)
            for w in workspaces:
                session.expunge(w)
            return workspaces

    def update_workspace(
        self,
        workspace_id: UUID,
        **kwargs,
    ) -> Optional[Workspace]:
        """Update workspace fields.

        Args:
            workspace_id: Workspace UUID
            **kwargs: Fields to update (name, slug, description, settings)

        Returns:
            Updated Workspace if found, None otherwise

        Raises:
            ValueError: If new slug is already taken by another workspace
        """
        with Session(engine) as session:
            workspace_repo = WorkspaceRepository(session)

            # Check slug uniqueness if being changed
            if "slug" in kwargs and kwargs["slug"]:
                existing = workspace_repo.get_by_slug(kwargs["slug"])
                if existing and existing.id != workspace_id:
                    raise ValueError("Slug is already taken")

            workspace = workspace_repo.update(workspace_id, **kwargs)
            if workspace:
                session.expunge(workspace)
            return workspace

    def delete_workspace(self, workspace_id: UUID) -> bool:
        """Delete a workspace and all associated data.

        This will cascade delete memberships. Content deletion should be
        handled separately or via database cascades.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if deleted, False if not found
        """
        with Session(engine) as session:
            workspace_repo = WorkspaceRepository(session)
            return workspace_repo.delete(workspace_id)

    def get_workspace_members(
        self, workspace_id: UUID
    ) -> list[WorkspaceMembership]:
        """Get all members of a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of WorkspaceMembership objects
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)
            members = membership_repo.list_by_workspace(workspace_id)
            for m in members:
                session.expunge(m)
            return members

    def get_user_membership(
        self, workspace_id: UUID, user_id: UUID
    ) -> Optional[WorkspaceMembership]:
        """Get a user's membership in a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID

        Returns:
            WorkspaceMembership if found, None otherwise
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)
            membership = membership_repo.get_by_workspace_and_user(
                workspace_id, user_id
            )
            if membership:
                session.expunge(membership)
            return membership

    def transfer_ownership(
        self,
        workspace_id: UUID,
        current_owner_id: UUID,
        new_owner_id: UUID,
    ) -> bool:
        """Transfer workspace ownership to another member.

        The new owner must already be a member of the workspace.
        The current owner becomes an admin.

        Args:
            workspace_id: Workspace UUID
            current_owner_id: Current owner's user UUID
            new_owner_id: New owner's user UUID

        Returns:
            True if transferred, False if conditions not met

        Raises:
            ValueError: If new owner is not a member
            ValueError: If current owner doesn't own the workspace
        """
        with Session(engine) as session:
            workspace_repo = WorkspaceRepository(session)
            membership_repo = WorkspaceMembershipRepository(session)

            # Get workspace
            workspace = workspace_repo.get(workspace_id)
            if not workspace:
                return False

            # Verify current owner
            if workspace.owner_id != current_owner_id:
                raise ValueError("Only the current owner can transfer ownership")

            # Get new owner's membership
            new_owner_membership = membership_repo.get_by_workspace_and_user(
                workspace_id, new_owner_id
            )
            if not new_owner_membership:
                raise ValueError("New owner must be a member of the workspace")

            # Get current owner's membership
            current_owner_membership = membership_repo.get_by_workspace_and_user(
                workspace_id, current_owner_id
            )

            # Update workspace owner_id
            workspace.owner_id = new_owner_id
            session.add(workspace)

            # Update membership roles
            new_owner_membership.role = WorkspaceRole.owner
            session.add(new_owner_membership)

            if current_owner_membership:
                current_owner_membership.role = WorkspaceRole.admin
                session.add(current_owner_membership)

            session.commit()
            return True
