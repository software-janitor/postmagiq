"""Approval service for managing content approval workflows.

Provides:
- Approval stage management
- Submitting posts for approval
- Approving/rejecting requests
- Tracking assignment history
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from runner.db.models import (
    Post,
    ApprovalStatus,
    AssignmentAction,
    PostAssignmentHistory,
    ApprovalStage,
    ApprovalRequest,
    ApprovalComment,
)


class ApprovalServiceError(Exception):
    """Base exception for approval service errors."""
    pass


class StageNotFoundError(ApprovalServiceError):
    """Raised when approval stage is not found."""
    pass


class RequestNotFoundError(ApprovalServiceError):
    """Raised when approval request is not found."""
    pass


class InvalidTransitionError(ApprovalServiceError):
    """Raised when an invalid status transition is attempted."""
    pass


class ApprovalService:
    """Service for managing approval workflows."""

    # ==========================================================================
    # Approval Stages
    # ==========================================================================

    def get_workspace_stages(
        self,
        session: Session,
        workspace_id: UUID,
        include_inactive: bool = False,
    ) -> list[ApprovalStage]:
        """Get all approval stages for a workspace, ordered by stage order."""
        stmt = select(ApprovalStage).where(
            ApprovalStage.workspace_id == workspace_id
        ).order_by(ApprovalStage.order)

        if not include_inactive:
            stmt = stmt.where(ApprovalStage.is_active == True)

        return list(session.exec(stmt).all())

    def create_stage(
        self,
        session: Session,
        workspace_id: UUID,
        created_by_id: UUID,
        name: str,
        description: Optional[str] = None,
        order: int = 0,
        is_required: bool = True,
        auto_approve_role: Optional[str] = None,
    ) -> ApprovalStage:
        """Create a new approval stage."""
        stage = ApprovalStage(
            workspace_id=workspace_id,
            created_by_id=created_by_id,
            name=name,
            description=description,
            order=order,
            is_required=is_required,
            auto_approve_role=auto_approve_role,
        )
        session.add(stage)
        session.commit()
        session.refresh(stage)
        return stage

    def update_stage(
        self,
        session: Session,
        stage_id: UUID,
        workspace_id: UUID,
        **updates,
    ) -> ApprovalStage:
        """Update an approval stage."""
        stage = session.get(ApprovalStage, stage_id)
        if not stage or stage.workspace_id != workspace_id:
            raise StageNotFoundError(f"Stage {stage_id} not found")

        for field, value in updates.items():
            if hasattr(stage, field) and value is not None:
                setattr(stage, field, value)

        session.add(stage)
        session.commit()
        session.refresh(stage)
        return stage

    def delete_stage(
        self,
        session: Session,
        stage_id: UUID,
        workspace_id: UUID,
    ) -> bool:
        """Soft-delete an approval stage by deactivating it."""
        stage = session.get(ApprovalStage, stage_id)
        if not stage or stage.workspace_id != workspace_id:
            raise StageNotFoundError(f"Stage {stage_id} not found")

        stage.is_active = False
        session.add(stage)
        session.commit()
        return True

    def ensure_default_stages(
        self,
        session: Session,
        workspace_id: UUID,
        created_by_id: UUID,
    ) -> list[ApprovalStage]:
        """Create default approval stages if none exist."""
        existing = self.get_workspace_stages(session, workspace_id, include_inactive=True)
        if existing:
            return existing

        default_stages = [
            {"name": "Draft Review", "order": 1, "is_required": True},
            {"name": "Final Approval", "order": 2, "is_required": True},
        ]

        stages = []
        for stage_data in default_stages:
            stage = self.create_stage(
                session,
                workspace_id,
                created_by_id,
                **stage_data,
            )
            stages.append(stage)

        return stages

    # ==========================================================================
    # Assignment Management
    # ==========================================================================

    def assign_post(
        self,
        session: Session,
        post_id: UUID,
        workspace_id: UUID,
        assigned_by_id: UUID,
        new_assignee_id: Optional[UUID],
        notes: Optional[str] = None,
    ) -> PostAssignmentHistory:
        """Assign or reassign a post to a user."""
        post = session.get(Post, post_id)
        if not post or post.workspace_id != workspace_id:
            raise ApprovalServiceError(f"Post {post_id} not found")

        previous_assignee_id = post.assignee_id
        action = (
            AssignmentAction.UNASSIGNED.value if new_assignee_id is None
            else AssignmentAction.ASSIGNED.value if previous_assignee_id is None
            else AssignmentAction.REASSIGNED.value
        )

        # Create history record
        history = PostAssignmentHistory(
            post_id=post_id,
            workspace_id=workspace_id,
            assigned_by_id=assigned_by_id,
            previous_assignee_id=previous_assignee_id,
            new_assignee_id=new_assignee_id,
            action=action,
            notes=notes,
        )
        session.add(history)

        # Update post
        post.assignee_id = new_assignee_id
        session.add(post)

        session.commit()
        session.refresh(history)
        return history

    def get_assignment_history(
        self,
        session: Session,
        post_id: UUID,
        workspace_id: UUID,
    ) -> list[PostAssignmentHistory]:
        """Get assignment history for a post."""
        stmt = select(PostAssignmentHistory).where(
            PostAssignmentHistory.post_id == post_id,
            PostAssignmentHistory.workspace_id == workspace_id,
        ).order_by(PostAssignmentHistory.created_at.desc())

        return list(session.exec(stmt).all())

    # ==========================================================================
    # Approval Requests
    # ==========================================================================

    def submit_for_approval(
        self,
        session: Session,
        post_id: UUID,
        workspace_id: UUID,
        submitted_by_id: UUID,
        stage_id: Optional[UUID] = None,
        assigned_approver_id: Optional[UUID] = None,
    ) -> ApprovalRequest:
        """Submit a post for approval.

        If no stage_id is provided, uses the first required stage.
        """
        post = session.get(Post, post_id)
        if not post or post.workspace_id != workspace_id:
            raise ApprovalServiceError(f"Post {post_id} not found")

        # Get or determine stage
        if stage_id:
            stage = session.get(ApprovalStage, stage_id)
            if not stage or stage.workspace_id != workspace_id:
                raise StageNotFoundError(f"Stage {stage_id} not found")
        else:
            stages = self.get_workspace_stages(session, workspace_id)
            if not stages:
                # Create default stages
                stages = self.ensure_default_stages(session, workspace_id, submitted_by_id)
            stage = stages[0]  # First stage

        # Check for existing pending request at this stage
        existing = session.exec(
            select(ApprovalRequest).where(
                ApprovalRequest.post_id == post_id,
                ApprovalRequest.stage_id == stage.id,
                ApprovalRequest.status == ApprovalStatus.PENDING.value,
            )
        ).first()

        if existing:
            raise ApprovalServiceError(
                f"Post already has pending approval request at stage {stage.name}"
            )

        request = ApprovalRequest(
            post_id=post_id,
            workspace_id=workspace_id,
            stage_id=stage.id,
            submitted_by_id=submitted_by_id,
            assigned_approver_id=assigned_approver_id,
            status=ApprovalStatus.PENDING.value,
        )
        session.add(request)

        # Update post status
        post.status = "pending_approval"
        session.add(post)

        session.commit()
        session.refresh(request)
        return request

    def approve(
        self,
        session: Session,
        request_id: UUID,
        workspace_id: UUID,
        decided_by_id: UUID,
        notes: Optional[str] = None,
        advance_to_next_stage: bool = True,
    ) -> ApprovalRequest:
        """Approve an approval request."""
        request = session.get(ApprovalRequest, request_id)
        if not request or request.workspace_id != workspace_id:
            raise RequestNotFoundError(f"Request {request_id} not found")

        if request.status != ApprovalStatus.PENDING.value:
            raise InvalidTransitionError(
                f"Cannot approve request with status {request.status}"
            )

        request.status = ApprovalStatus.APPROVED.value
        request.decided_by_id = decided_by_id
        request.decided_at = datetime.utcnow()
        request.decision_notes = notes
        session.add(request)

        # Get post and stage info
        post = session.get(Post, request.post_id)
        stage = session.get(ApprovalStage, request.stage_id)

        if advance_to_next_stage:
            # Check for next stage
            next_stages = session.exec(
                select(ApprovalStage).where(
                    ApprovalStage.workspace_id == workspace_id,
                    ApprovalStage.is_active == True,
                    ApprovalStage.order > stage.order,
                ).order_by(ApprovalStage.order)
            ).all()

            if next_stages:
                # Create request for next stage
                next_request = ApprovalRequest(
                    post_id=request.post_id,
                    workspace_id=workspace_id,
                    stage_id=next_stages[0].id,
                    submitted_by_id=request.submitted_by_id,
                    status=ApprovalStatus.PENDING.value,
                )
                session.add(next_request)
            else:
                # All stages complete - mark post as approved/ready
                post.status = "ready"
                session.add(post)
        else:
            # Not advancing - post remains in pending state
            pass

        session.commit()
        session.refresh(request)
        return request

    def reject(
        self,
        session: Session,
        request_id: UUID,
        workspace_id: UUID,
        decided_by_id: UUID,
        notes: str,
    ) -> ApprovalRequest:
        """Reject an approval request."""
        request = session.get(ApprovalRequest, request_id)
        if not request or request.workspace_id != workspace_id:
            raise RequestNotFoundError(f"Request {request_id} not found")

        if request.status != ApprovalStatus.PENDING.value:
            raise InvalidTransitionError(
                f"Cannot reject request with status {request.status}"
            )

        request.status = ApprovalStatus.REJECTED.value
        request.decided_by_id = decided_by_id
        request.decided_at = datetime.utcnow()
        request.decision_notes = notes
        session.add(request)

        # Update post status back to draft
        post = session.get(Post, request.post_id)
        post.status = "draft"
        session.add(post)

        session.commit()
        session.refresh(request)
        return request

    def request_changes(
        self,
        session: Session,
        request_id: UUID,
        workspace_id: UUID,
        decided_by_id: UUID,
        notes: str,
    ) -> ApprovalRequest:
        """Request changes on an approval request."""
        request = session.get(ApprovalRequest, request_id)
        if not request or request.workspace_id != workspace_id:
            raise RequestNotFoundError(f"Request {request_id} not found")

        if request.status != ApprovalStatus.PENDING.value:
            raise InvalidTransitionError(
                f"Cannot request changes on request with status {request.status}"
            )

        request.status = ApprovalStatus.CHANGES_REQUESTED.value
        request.decided_by_id = decided_by_id
        request.decided_at = datetime.utcnow()
        request.decision_notes = notes
        session.add(request)

        # Update post status
        post = session.get(Post, request.post_id)
        post.status = "changes_requested"
        session.add(post)

        session.commit()
        session.refresh(request)
        return request

    def withdraw(
        self,
        session: Session,
        request_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> ApprovalRequest:
        """Withdraw an approval request (by submitter)."""
        request = session.get(ApprovalRequest, request_id)
        if not request or request.workspace_id != workspace_id:
            raise RequestNotFoundError(f"Request {request_id} not found")

        if request.submitted_by_id != user_id:
            raise ApprovalServiceError("Only the submitter can withdraw a request")

        if request.status != ApprovalStatus.PENDING.value:
            raise InvalidTransitionError(
                f"Cannot withdraw request with status {request.status}"
            )

        request.status = ApprovalStatus.WITHDRAWN.value
        session.add(request)

        # Update post status back to draft
        post = session.get(Post, request.post_id)
        post.status = "draft"
        session.add(post)

        session.commit()
        session.refresh(request)
        return request

    def get_pending_approvals(
        self,
        session: Session,
        workspace_id: UUID,
        approver_id: Optional[UUID] = None,
    ) -> list[ApprovalRequest]:
        """Get pending approval requests.

        If approver_id is provided, returns requests assigned to that user
        or requests with no specific assignee.
        """
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.workspace_id == workspace_id,
            ApprovalRequest.status == ApprovalStatus.PENDING.value,
        )

        if approver_id:
            stmt = stmt.where(
                (ApprovalRequest.assigned_approver_id == approver_id) |
                (ApprovalRequest.assigned_approver_id == None)
            )

        stmt = stmt.order_by(ApprovalRequest.submitted_at)
        return list(session.exec(stmt).all())

    def get_post_approval_history(
        self,
        session: Session,
        post_id: UUID,
        workspace_id: UUID,
    ) -> list[ApprovalRequest]:
        """Get all approval requests for a post."""
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.post_id == post_id,
            ApprovalRequest.workspace_id == workspace_id,
        ).order_by(ApprovalRequest.submitted_at.desc())

        return list(session.exec(stmt).all())

    # ==========================================================================
    # Comments
    # ==========================================================================

    def add_comment(
        self,
        session: Session,
        request_id: UUID,
        workspace_id: UUID,
        author_id: UUID,
        content: str,
        is_internal: bool = False,
        line_reference: Optional[str] = None,
    ) -> ApprovalComment:
        """Add a comment to an approval request."""
        request = session.get(ApprovalRequest, request_id)
        if not request or request.workspace_id != workspace_id:
            raise RequestNotFoundError(f"Request {request_id} not found")

        comment = ApprovalComment(
            approval_request_id=request_id,
            workspace_id=workspace_id,
            author_id=author_id,
            content=content,
            is_internal=is_internal,
            line_reference=line_reference,
        )
        session.add(comment)
        session.commit()
        session.refresh(comment)
        return comment

    def get_comments(
        self,
        session: Session,
        request_id: UUID,
        workspace_id: UUID,
        include_internal: bool = True,
    ) -> list[ApprovalComment]:
        """Get comments for an approval request."""
        stmt = select(ApprovalComment).where(
            ApprovalComment.approval_request_id == request_id,
            ApprovalComment.workspace_id == workspace_id,
        )

        if not include_internal:
            stmt = stmt.where(ApprovalComment.is_internal == False)

        stmt = stmt.order_by(ApprovalComment.created_at)
        return list(session.exec(stmt).all())
