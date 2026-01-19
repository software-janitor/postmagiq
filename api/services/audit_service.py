"""Audit service for logging and querying audit events.

Provides:
- Logging actions with before/after values
- Querying audit logs with filters
- Pagination support for audit log queries
"""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from fastapi import Request
from sqlmodel import Session, select, func, col

from runner.db.models.audit import (
    AuditAction,
    AuditLog,
    AuditLogCreate,
    AuditLogRead,
)
from runner.logging.structured import get_logger

logger = get_logger(__name__)


class AuditServiceError(Exception):
    """Base exception for audit service errors."""
    pass


class AuditNotFoundError(AuditServiceError):
    """Raised when an audit log entry is not found."""
    pass


class AuditService:
    """Service for managing audit logs.

    Provides methods for logging actions and querying the audit trail.
    All significant actions in the system should be logged through this service.
    """

    # ==========================================================================
    # Logging Actions
    # ==========================================================================

    def log_action(
        self,
        session: Session,
        workspace_id: UUID,
        user_id: UUID,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        old_value: Optional[dict[str, Any]] = None,
        new_value: Optional[dict[str, Any]] = None,
        request: Optional[Request] = None,
        description: Optional[str] = None,
    ) -> AuditLog:
        """Log an auditable action.

        Args:
            session: Database session
            workspace_id: Workspace where the action occurred
            user_id: User who performed the action
            action: Type of action from AuditAction enum
            resource_type: Type of resource affected (e.g., "post", "workflow")
            resource_id: ID of the specific resource (optional)
            old_value: Previous state as dict (for updates/deletes)
            new_value: New state as dict (for creates/updates)
            request: FastAPI request object for extracting client info
            description: Human-readable description of the action

        Returns:
            Created AuditLog entry
        """
        # Extract request metadata
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            # Truncate user agent if too long
            if user_agent and len(user_agent) > 500:
                user_agent = user_agent[:497] + "..."

        audit_log = AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )

        session.add(audit_log)
        session.commit()
        session.refresh(audit_log)

        # Also log to structured logging
        logger.info(
            "audit_action_logged",
            audit_id=str(audit_log.id),
            workspace_id=str(workspace_id),
            user_id=str(user_id),
            action=action.value,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
        )

        return audit_log

    def log_create(
        self,
        session: Session,
        workspace_id: UUID,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        new_value: dict[str, Any],
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Convenience method for logging create actions."""
        return self.log_action(
            session=session,
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditAction.create,
            resource_type=resource_type,
            resource_id=resource_id,
            new_value=new_value,
            request=request,
            description=f"Created {resource_type}",
        )

    def log_update(
        self,
        session: Session,
        workspace_id: UUID,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Convenience method for logging update actions."""
        return self.log_action(
            session=session,
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditAction.update,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            request=request,
            description=f"Updated {resource_type}",
        )

    def log_delete(
        self,
        session: Session,
        workspace_id: UUID,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        old_value: dict[str, Any],
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Convenience method for logging delete actions."""
        return self.log_action(
            session=session,
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditAction.delete,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            request=request,
            description=f"Deleted {resource_type}",
        )

    # ==========================================================================
    # Querying Audit Logs
    # ==========================================================================

    def get_audit_logs(
        self,
        session: Session,
        workspace_id: UUID,
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Get audit logs with filtering and pagination.

        Args:
            session: Database session
            workspace_id: Workspace to filter by
            user_id: Optional user filter
            action: Optional action type filter
            resource_type: Optional resource type filter
            resource_id: Optional specific resource filter
            start_date: Optional start of date range
            end_date: Optional end of date range
            limit: Maximum results to return (default 50)
            offset: Number of results to skip (default 0)

        Returns:
            Tuple of (list of AuditLog, total count)
        """
        # Build base query
        stmt = select(AuditLog).where(AuditLog.workspace_id == workspace_id)

        # Apply filters
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if resource_id:
            stmt = stmt.where(AuditLog.resource_id == resource_id)
        if start_date:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.exec(count_stmt).one()

        # Apply pagination and ordering
        stmt = stmt.order_by(col(AuditLog.created_at).desc()).offset(offset).limit(limit)

        logs = list(session.exec(stmt).all())

        return logs, total

    def get_audit_log(
        self,
        session: Session,
        audit_id: UUID,
        workspace_id: UUID,
    ) -> AuditLog:
        """Get a single audit log entry by ID.

        Args:
            session: Database session
            audit_id: ID of the audit log entry
            workspace_id: Workspace ID (for access control)

        Returns:
            AuditLog entry

        Raises:
            AuditNotFoundError: If entry not found or wrong workspace
        """
        audit_log = session.get(AuditLog, audit_id)
        if not audit_log or audit_log.workspace_id != workspace_id:
            raise AuditNotFoundError(f"Audit log {audit_id} not found")
        return audit_log

    def get_resource_history(
        self,
        session: Session,
        workspace_id: UUID,
        resource_type: str,
        resource_id: UUID,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get the complete audit history for a specific resource.

        Useful for showing "activity timeline" on a resource detail page.

        Args:
            session: Database session
            workspace_id: Workspace ID
            resource_type: Type of resource
            resource_id: ID of the resource
            limit: Maximum entries to return

        Returns:
            List of AuditLog entries, ordered by most recent first
        """
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.workspace_id == workspace_id,
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(col(AuditLog.created_at).desc())
            .limit(limit)
        )

        return list(session.exec(stmt).all())

    def get_user_activity(
        self,
        session: Session,
        workspace_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Get recent activity for a specific user in a workspace.

        Useful for user activity dashboards.

        Args:
            session: Database session
            workspace_id: Workspace ID
            user_id: User ID
            limit: Maximum entries to return

        Returns:
            List of AuditLog entries, ordered by most recent first
        """
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.workspace_id == workspace_id,
                AuditLog.user_id == user_id,
            )
            .order_by(col(AuditLog.created_at).desc())
            .limit(limit)
        )

        return list(session.exec(stmt).all())

    # ==========================================================================
    # Conversion Helpers
    # ==========================================================================

    def to_read(self, audit_log: AuditLog) -> AuditLogRead:
        """Convert AuditLog to AuditLogRead schema."""
        return AuditLogRead(
            id=audit_log.id,
            workspace_id=audit_log.workspace_id,
            user_id=audit_log.user_id,
            action=audit_log.action,
            resource_type=audit_log.resource_type,
            resource_id=audit_log.resource_id,
            old_value=audit_log.old_value,
            new_value=audit_log.new_value,
            description=audit_log.description,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            created_at=audit_log.created_at,
        )
