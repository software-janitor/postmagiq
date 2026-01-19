"""Audit log model for tracking system changes.

Provides a comprehensive audit trail of all significant actions
within workspaces for security, compliance, and debugging.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import UUID

from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON, Text

from runner.db.models.base import UUIDModel


class AuditAction(str, Enum):
    """Types of auditable actions.

    Organized by category:
    - Auth: login, logout, token_refresh
    - CRUD: create, read, update, delete
    - Workflow: workflow_started, workflow_completed, workflow_failed
    - Access: permission_granted, permission_revoked
    - System: settings_changed, export, import
    """

    # Authentication
    login = "login"
    logout = "logout"
    token_refresh = "token_refresh"
    password_changed = "password_changed"

    # CRUD operations
    create = "create"
    read = "read"
    update = "update"
    delete = "delete"

    # Workflow operations
    workflow_started = "workflow_started"
    workflow_completed = "workflow_completed"
    workflow_failed = "workflow_failed"
    workflow_cancelled = "workflow_cancelled"

    # Access management
    permission_granted = "permission_granted"
    permission_revoked = "permission_revoked"
    invite_sent = "invite_sent"
    invite_accepted = "invite_accepted"
    member_removed = "member_removed"

    # System operations
    settings_changed = "settings_changed"
    export = "export"
    import_data = "import"
    api_key_created = "api_key_created"
    api_key_revoked = "api_key_revoked"
    webhook_created = "webhook_created"
    webhook_deleted = "webhook_deleted"


class AuditLogBase(SQLModel):
    """Base audit log fields shared across Create/Read."""

    action: AuditAction
    resource_type: str = Field(max_length=100)
    resource_id: Optional[UUID] = None
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)


class AuditLog(UUIDModel, AuditLogBase, table=True):
    """Audit log table for tracking all significant actions.

    Every auditable action creates a record with:
    - Who did it (user_id)
    - In what context (workspace_id)
    - What action (action enum)
    - On what resource (resource_type, resource_id)
    - What changed (old_value, new_value as JSON)
    - Request metadata (ip_address, user_agent)
    """

    __tablename__ = "audit_logs"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)

    # JSON columns for storing before/after state
    old_value: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    new_value: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    # Additional context for the action
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    # Timestamp only (no updated_at since audit logs are immutable)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        index=True,
    )


class AuditLogCreate(AuditLogBase):
    """Schema for creating a new audit log entry."""

    workspace_id: UUID
    user_id: UUID
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    description: Optional[str] = None


class AuditLogRead(AuditLogBase):
    """Schema for reading audit log data."""

    id: UUID
    workspace_id: UUID
    user_id: UUID
    old_value: Optional[dict[str, Any]]
    new_value: Optional[dict[str, Any]]
    description: Optional[str]
    created_at: datetime
