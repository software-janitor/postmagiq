"""Portal service for client-facing content review workflows.

Provides:
- Posts pending client approval
- Client approval/rejection of posts
- Workspace branding retrieval
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from runner.db.models import (
    Post,
    ApprovalRequest,
    ApprovalStatus,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
    InviteStatus,
    WhitelabelConfig,
)


class PortalServiceError(Exception):
    """Base exception for portal service errors."""
    pass


class PostNotFoundError(PortalServiceError):
    """Raised when a post is not found."""
    pass


class UnauthorizedError(PortalServiceError):
    """Raised when a user is not authorized for an action."""
    pass


class InvalidStateError(PortalServiceError):
    """Raised when an action is invalid for the current state."""
    pass


class PortalService:
    """Service for client portal operations.

    Provides read-only access to posts and approval functionality
    for client users (viewers).
    """

    def get_workspace_branding(
        self,
        session: Session,
        workspace_id: UUID,
    ) -> Optional[dict]:
        """Get workspace branding configuration for portal display.

        Args:
            session: Database session
            workspace_id: Workspace UUID

        Returns:
            Dict with branding info or None if not configured
        """
        # Get workspace
        workspace = session.get(Workspace, workspace_id)
        if not workspace:
            return None

        # Get whitelabel config
        whitelabel = session.exec(
            select(WhitelabelConfig).where(
                WhitelabelConfig.workspace_id == workspace_id
            )
        ).first()

        branding = {
            "workspace_name": workspace.name,
            "workspace_slug": workspace.slug,
        }

        if whitelabel and whitelabel.is_active:
            branding.update({
                "company_name": whitelabel.company_name or workspace.name,
                "logo_url": whitelabel.logo_url,
                "logo_dark_url": whitelabel.logo_dark_url,
                "favicon_url": whitelabel.favicon_url,
                "primary_color": whitelabel.primary_color,
                "secondary_color": whitelabel.secondary_color,
                "accent_color": whitelabel.accent_color,
                "portal_welcome_text": whitelabel.portal_welcome_text,
                "portal_footer_text": whitelabel.portal_footer_text,
                "support_email": whitelabel.support_email,
            })
        else:
            branding.update({
                "company_name": workspace.name,
                "logo_url": None,
                "logo_dark_url": None,
                "favicon_url": None,
                "primary_color": None,
                "secondary_color": None,
                "accent_color": None,
                "portal_welcome_text": None,
                "portal_footer_text": None,
                "support_email": None,
            })

        return branding

    def get_posts_for_review(
        self,
        session: Session,
        workspace_id: UUID,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        """Get posts pending client approval.

        Args:
            session: Database session
            workspace_id: Workspace UUID
            status_filter: Optional status filter (e.g., "pending_approval")

        Returns:
            List of post dicts with approval info
        """
        # Query posts in the workspace that need review
        stmt = select(Post).where(Post.workspace_id == workspace_id)

        if status_filter:
            stmt = stmt.where(Post.status == status_filter)
        else:
            # Default: posts that are in review-related statuses
            stmt = stmt.where(
                Post.status.in_([
                    "pending_approval",
                    "ready",
                    "changes_requested",
                ])
            )

        stmt = stmt.order_by(Post.post_number)
        posts = list(session.exec(stmt).all())

        result = []
        for post in posts:
            # Get the latest approval request for this post
            approval_stmt = select(ApprovalRequest).where(
                ApprovalRequest.post_id == post.id,
                ApprovalRequest.workspace_id == workspace_id,
            ).order_by(ApprovalRequest.submitted_at.desc())

            latest_approval = session.exec(approval_stmt).first()

            post_dict = {
                "id": str(post.id),
                "post_number": post.post_number,
                "topic": post.topic,
                "shape": post.shape,
                "cadence": post.cadence,
                "status": post.status,
                "due_date": post.due_date.isoformat() if post.due_date else None,
                "priority": post.priority,
                "approval_status": latest_approval.status if latest_approval else None,
                "submitted_at": (
                    latest_approval.submitted_at.isoformat()
                    if latest_approval
                    else None
                ),
            }
            result.append(post_dict)

        return result

    def get_post_detail(
        self,
        session: Session,
        workspace_id: UUID,
        post_id: UUID,
    ) -> Optional[dict]:
        """Get detailed post information for client review.

        Args:
            session: Database session
            workspace_id: Workspace UUID
            post_id: Post UUID

        Returns:
            Post detail dict or None if not found
        """
        post = session.get(Post, post_id)
        if not post or post.workspace_id != workspace_id:
            return None

        # Get latest approval request
        approval_stmt = select(ApprovalRequest).where(
            ApprovalRequest.post_id == post_id,
            ApprovalRequest.workspace_id == workspace_id,
        ).order_by(ApprovalRequest.submitted_at.desc())

        latest_approval = session.exec(approval_stmt).first()

        return {
            "id": str(post.id),
            "post_number": post.post_number,
            "topic": post.topic,
            "shape": post.shape,
            "cadence": post.cadence,
            "entry_point": post.entry_point,
            "status": post.status,
            "guidance": post.guidance,
            "due_date": post.due_date.isoformat() if post.due_date else None,
            "priority": post.priority,
            "approval_request_id": (
                str(latest_approval.id) if latest_approval else None
            ),
            "approval_status": latest_approval.status if latest_approval else None,
            "decision_notes": latest_approval.decision_notes if latest_approval else None,
            "submitted_at": (
                latest_approval.submitted_at.isoformat()
                if latest_approval
                else None
            ),
        }

    def approve_post(
        self,
        session: Session,
        workspace_id: UUID,
        post_id: UUID,
        client_user_id: UUID,
        notes: Optional[str] = None,
    ) -> ApprovalRequest:
        """Approve a post as a client.

        Args:
            session: Database session
            workspace_id: Workspace UUID
            post_id: Post UUID
            client_user_id: The client user approving
            notes: Optional approval notes

        Returns:
            Updated ApprovalRequest

        Raises:
            PostNotFoundError: If post not found
            UnauthorizedError: If user not authorized
            InvalidStateError: If post not in reviewable state
        """
        # Verify user is a member of the workspace (viewer is sufficient)
        membership = session.exec(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == client_user_id,
                WorkspaceMembership.invite_status == InviteStatus.accepted,
            )
        ).first()

        if not membership:
            raise UnauthorizedError("User is not a member of this workspace")

        # Get post
        post = session.get(Post, post_id)
        if not post or post.workspace_id != workspace_id:
            raise PostNotFoundError(f"Post {post_id} not found")

        # Get latest pending approval request
        approval_request = session.exec(
            select(ApprovalRequest).where(
                ApprovalRequest.post_id == post_id,
                ApprovalRequest.workspace_id == workspace_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value,
            )
        ).first()

        if not approval_request:
            raise InvalidStateError("No pending approval request for this post")

        # Update approval request
        approval_request.status = ApprovalStatus.APPROVED.value
        approval_request.decided_by_id = client_user_id
        approval_request.decided_at = datetime.utcnow()
        approval_request.decision_notes = notes
        session.add(approval_request)

        # Update post status
        post.status = "ready"
        session.add(post)

        session.commit()
        session.refresh(approval_request)
        return approval_request

    def reject_post(
        self,
        session: Session,
        workspace_id: UUID,
        post_id: UUID,
        client_user_id: UUID,
        feedback: str,
    ) -> ApprovalRequest:
        """Reject a post as a client with feedback.

        Args:
            session: Database session
            workspace_id: Workspace UUID
            post_id: Post UUID
            client_user_id: The client user rejecting
            feedback: Required feedback explaining rejection

        Returns:
            Updated ApprovalRequest

        Raises:
            PostNotFoundError: If post not found
            UnauthorizedError: If user not authorized
            InvalidStateError: If post not in reviewable state
        """
        if not feedback or not feedback.strip():
            raise InvalidStateError("Feedback is required when rejecting a post")

        # Verify user is a member of the workspace
        membership = session.exec(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == client_user_id,
                WorkspaceMembership.invite_status == InviteStatus.accepted,
            )
        ).first()

        if not membership:
            raise UnauthorizedError("User is not a member of this workspace")

        # Get post
        post = session.get(Post, post_id)
        if not post or post.workspace_id != workspace_id:
            raise PostNotFoundError(f"Post {post_id} not found")

        # Get latest pending approval request
        approval_request = session.exec(
            select(ApprovalRequest).where(
                ApprovalRequest.post_id == post_id,
                ApprovalRequest.workspace_id == workspace_id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value,
            )
        ).first()

        if not approval_request:
            raise InvalidStateError("No pending approval request for this post")

        # Update approval request
        approval_request.status = ApprovalStatus.REJECTED.value
        approval_request.decided_by_id = client_user_id
        approval_request.decided_at = datetime.utcnow()
        approval_request.decision_notes = feedback
        session.add(approval_request)

        # Update post status back to changes_requested
        post.status = "changes_requested"
        session.add(post)

        session.commit()
        session.refresh(approval_request)
        return approval_request

    def authenticate_portal_user(
        self,
        session: Session,
        email: str,
        password: str,
        workspace_id: UUID,
    ) -> Optional[dict]:
        """Authenticate a user for portal access (viewer scope only).

        This is a limited authentication that only grants viewer access
        to a specific workspace.

        Args:
            session: Database session
            email: User email
            password: User password
            workspace_id: Workspace to authenticate for

        Returns:
            Dict with user info and workspace access, or None if auth fails
        """
        from api.auth.password import verify_password

        # Find user by email
        user = session.exec(
            select(User).where(User.email == email)
        ).first()

        if not user:
            return None

        if not user.password_hash or not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        # Check workspace membership
        membership = session.exec(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.invite_status == InviteStatus.accepted,
            )
        ).first()

        if not membership:
            return None

        return {
            "user_id": str(user.id),
            "email": user.email,
            "name": user.name,
            "workspace_id": str(workspace_id),
            "role": membership.role.value,
        }
