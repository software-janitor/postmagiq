"""Tests for audit log models, service, and routes."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime


class TestAuditModels:
    """Tests for audit model definitions."""

    def test_audit_action_enum(self):
        """AuditAction enum has expected values."""
        from runner.db.models import AuditAction

        # Authentication actions
        assert AuditAction.login == "login"
        assert AuditAction.logout == "logout"
        assert AuditAction.token_refresh == "token_refresh"
        assert AuditAction.password_changed == "password_changed"

        # CRUD actions
        assert AuditAction.create == "create"
        assert AuditAction.read == "read"
        assert AuditAction.update == "update"
        assert AuditAction.delete == "delete"

        # Workflow actions
        assert AuditAction.workflow_started == "workflow_started"
        assert AuditAction.workflow_completed == "workflow_completed"
        assert AuditAction.workflow_failed == "workflow_failed"

        # Access management
        assert AuditAction.permission_granted == "permission_granted"
        assert AuditAction.invite_sent == "invite_sent"
        assert AuditAction.member_removed == "member_removed"

    def test_audit_log_model(self):
        """AuditLog model can be instantiated."""
        from runner.db.models import AuditLog, AuditAction

        workspace_id = uuid4()
        user_id = uuid4()
        resource_id = uuid4()

        audit_log = AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditAction.create,
            resource_type="post",
            resource_id=resource_id,
            new_value={"title": "New Post"},
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
        )

        assert audit_log.workspace_id == workspace_id
        assert audit_log.user_id == user_id
        assert audit_log.action == AuditAction.create
        assert audit_log.resource_type == "post"
        assert audit_log.resource_id == resource_id
        assert audit_log.new_value == {"title": "New Post"}
        assert audit_log.old_value is None
        assert audit_log.ip_address == "127.0.0.1"

    def test_audit_log_with_old_and_new_value(self):
        """AuditLog can store before/after state."""
        from runner.db.models import AuditLog, AuditAction

        workspace_id = uuid4()
        user_id = uuid4()

        audit_log = AuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditAction.update,
            resource_type="post",
            old_value={"title": "Old Title"},
            new_value={"title": "New Title"},
        )

        assert audit_log.old_value == {"title": "Old Title"}
        assert audit_log.new_value == {"title": "New Title"}

    def test_audit_log_create_schema(self):
        """AuditLogCreate schema can be instantiated."""
        from runner.db.models.audit import AuditLogCreate, AuditAction

        workspace_id = uuid4()
        user_id = uuid4()

        create_data = AuditLogCreate(
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditAction.create,
            resource_type="workflow",
            description="Started workflow",
        )

        assert create_data.workspace_id == workspace_id
        assert create_data.action == AuditAction.create
        assert create_data.resource_type == "workflow"

    def test_audit_log_read_schema(self):
        """AuditLogRead schema can be instantiated."""
        from runner.db.models.audit import AuditLogRead, AuditAction

        audit_id = uuid4()
        workspace_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()

        read_data = AuditLogRead(
            id=audit_id,
            workspace_id=workspace_id,
            user_id=user_id,
            action=AuditAction.delete,
            resource_type="post",
            resource_id=uuid4(),
            old_value={"title": "Deleted Post"},
            new_value=None,
            description="Deleted post",
            ip_address="192.168.1.1",
            user_agent="Test Client",
            created_at=now,
        )

        assert read_data.id == audit_id
        assert read_data.action == AuditAction.delete


class TestAuditService:
    """Tests for AuditService."""

    def test_audit_service_instantiation(self):
        """AuditService can be instantiated."""
        from api.services import AuditService

        service = AuditService()
        assert service is not None

    def test_audit_service_error_classes(self):
        """Service error classes exist."""
        from api.services import (
            AuditService,
            AuditServiceError,
            AuditNotFoundError,
        )

        # Errors should be proper exception subclasses
        assert issubclass(AuditNotFoundError, AuditServiceError)

    def test_audit_service_has_log_action_method(self):
        """AuditService has log_action method."""
        from api.services import AuditService

        service = AuditService()
        assert hasattr(service, "log_action")
        assert callable(service.log_action)

    def test_audit_service_has_convenience_methods(self):
        """AuditService has convenience methods."""
        from api.services import AuditService

        service = AuditService()
        assert hasattr(service, "log_create")
        assert hasattr(service, "log_update")
        assert hasattr(service, "log_delete")

    def test_audit_service_has_query_methods(self):
        """AuditService has query methods."""
        from api.services import AuditService

        service = AuditService()
        assert hasattr(service, "get_audit_logs")
        assert hasattr(service, "get_audit_log")
        assert hasattr(service, "get_resource_history")
        assert hasattr(service, "get_user_activity")


class TestAuditRoutes:
    """Tests for audit API routes."""

    def test_audit_log_response_model(self):
        """AuditLogResponse model structure."""
        from api.routes.v1.audit import AuditLogResponse

        audit_id = uuid4()
        workspace_id = uuid4()
        user_id = uuid4()
        resource_id = uuid4()
        now = datetime.utcnow()

        response = AuditLogResponse(
            id=audit_id,
            workspace_id=workspace_id,
            user_id=user_id,
            action="create",
            resource_type="post",
            resource_id=resource_id,
            old_value=None,
            new_value={"title": "New Post"},
            description="Created post",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            created_at=now,
        )

        assert response.id == audit_id
        assert response.action == "create"
        assert response.resource_type == "post"

    def test_audit_log_list_response_model(self):
        """AuditLogListResponse model structure."""
        from api.routes.v1.audit import AuditLogListResponse, AuditLogResponse

        now = datetime.utcnow()
        items = [
            AuditLogResponse(
                id=uuid4(),
                workspace_id=uuid4(),
                user_id=uuid4(),
                action="create",
                resource_type="post",
                resource_id=None,
                old_value=None,
                new_value=None,
                description=None,
                ip_address=None,
                user_agent=None,
                created_at=now,
            )
        ]

        response = AuditLogListResponse(
            items=items,
            total=1,
            limit=50,
            offset=0,
        )

        assert response.total == 1
        assert len(response.items) == 1
        assert response.limit == 50
        assert response.offset == 0


class TestStructuredLogging:
    """Tests for structured logging module."""

    def test_structured_logging_imports(self):
        """Structured logging functions can be imported."""
        from runner.logging import (
            configure_structlog,
            get_logger,
            bind_context,
            clear_context,
            with_context,
        )

        assert configure_structlog is not None
        assert get_logger is not None
        assert bind_context is not None
        assert clear_context is not None
        assert with_context is not None

    def test_get_logger_returns_bound_logger(self):
        """get_logger returns a structlog BoundLogger."""
        from runner.logging import get_logger

        logger = get_logger(__name__)
        assert logger is not None
        # Should have standard logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_bind_context_and_clear(self):
        """bind_context and clear_context work correctly."""
        from runner.logging.structured import bind_context, clear_context, _context_vars

        # Clear first
        clear_context()
        assert len(_context_vars) == 0

        # Bind some context
        user_id = uuid4()
        workspace_id = uuid4()
        bind_context(
            request_id="test-123",
            user_id=user_id,
            workspace_id=workspace_id,
        )

        assert _context_vars.get("request_id") == "test-123"
        assert _context_vars.get("user_id") == str(user_id)
        assert _context_vars.get("workspace_id") == str(workspace_id)

        # Clear context
        clear_context()
        assert len(_context_vars) == 0

    def test_with_context_returns_dict(self):
        """with_context returns the added context."""
        from runner.logging.structured import with_context, clear_context

        clear_context()

        ctx = with_context(operation="test", batch_id="batch-123")

        assert "operation" in ctx
        assert "batch_id" in ctx
        assert ctx["operation"] == "test"

        clear_context()

    def test_configure_structlog_json_mode(self):
        """configure_structlog can be called with JSON mode."""
        from runner.logging import configure_structlog

        # Should not raise
        configure_structlog(json_format=True, log_level="DEBUG")

        # Restore to dev mode for other tests
        configure_structlog(json_format=False, log_level="INFO")

    def test_configure_structlog_dev_mode(self):
        """configure_structlog can be called with dev mode."""
        from runner.logging import configure_structlog

        # Should not raise
        configure_structlog(json_format=False, log_level="INFO")


class TestAuditIntegration:
    """Integration tests for audit system."""

    def test_audit_models_import_from_init(self):
        """All audit models can be imported from __init__."""
        from runner.db.models import (
            AuditAction,
            AuditLog,
            AuditLogCreate,
            AuditLogRead,
        )

        # All should be importable
        assert AuditAction is not None
        assert AuditLog is not None
        assert AuditLogCreate is not None
        assert AuditLogRead is not None

    def test_service_import_from_init(self):
        """Audit service can be imported from __init__."""
        from api.services import (
            AuditService,
            AuditServiceError,
            AuditNotFoundError,
        )

        assert AuditService is not None
        assert AuditServiceError is not None
        assert AuditNotFoundError is not None

    def test_router_import_from_init(self):
        """Audit router can be imported from __init__."""
        from api.routes.v1 import audit_router

        assert audit_router is not None

    def test_structured_logging_import_from_logging_init(self):
        """Structured logging can be imported from logging __init__."""
        from runner.logging import (
            configure_structlog,
            get_logger,
            bind_context,
            clear_context,
        )

        assert configure_structlog is not None
        assert get_logger is not None
        assert bind_context is not None
        assert clear_context is not None


class TestAuditActionCompleteness:
    """Test that AuditAction enum covers expected use cases."""

    def test_crud_actions_exist(self):
        """CRUD actions are defined."""
        from runner.db.models import AuditAction

        crud_actions = {"create", "read", "update", "delete"}
        actual = {a.value for a in AuditAction if a.value in crud_actions}
        assert actual == crud_actions

    def test_auth_actions_exist(self):
        """Authentication actions are defined."""
        from runner.db.models import AuditAction

        auth_actions = {"login", "logout", "token_refresh", "password_changed"}
        actual = {a.value for a in AuditAction if a.value in auth_actions}
        assert actual == auth_actions

    def test_workflow_actions_exist(self):
        """Workflow actions are defined."""
        from runner.db.models import AuditAction

        workflow_actions = {
            "workflow_started",
            "workflow_completed",
            "workflow_failed",
            "workflow_cancelled",
        }
        actual = {a.value for a in AuditAction if a.value in workflow_actions}
        assert actual == workflow_actions

    def test_access_management_actions_exist(self):
        """Access management actions are defined."""
        from runner.db.models import AuditAction

        access_actions = {
            "permission_granted",
            "permission_revoked",
            "invite_sent",
            "invite_accepted",
            "member_removed",
        }
        actual = {a.value for a in AuditAction if a.value in access_actions}
        assert actual == access_actions
