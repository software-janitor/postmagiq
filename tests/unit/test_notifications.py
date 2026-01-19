"""Tests for notification models, service, and routes."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime


class TestNotificationModels:
    """Tests for notification model definitions."""

    def test_notification_channel_type_enum(self):
        """NotificationChannelType enum has expected values."""
        from runner.db.models import NotificationChannelType

        assert NotificationChannelType.IN_APP == "in_app"
        assert NotificationChannelType.EMAIL == "email"

    def test_notification_type_enum(self):
        """NotificationType enum has expected values."""
        from runner.db.models import NotificationType

        # Approval-related
        assert NotificationType.APPROVAL_REQUESTED == "approval_requested"
        assert NotificationType.APPROVAL_APPROVED == "approval_approved"
        assert NotificationType.APPROVAL_REJECTED == "approval_rejected"

        # Assignment-related
        assert NotificationType.POST_ASSIGNED == "post_assigned"

        # Team-related
        assert NotificationType.MEMBER_JOINED == "member_joined"

    def test_notification_priority_enum(self):
        """NotificationPriority enum has expected values."""
        from runner.db.models import NotificationPriority

        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.NORMAL == "normal"
        assert NotificationPriority.HIGH == "high"
        assert NotificationPriority.URGENT == "urgent"

    def test_notification_channel_model(self):
        """NotificationChannel model can be instantiated."""
        from runner.db.models import NotificationChannel, NotificationChannelType

        channel = NotificationChannel(
            channel_type=NotificationChannelType.IN_APP.value,
            name="In-App",
            description="In-app notifications",
            is_enabled=True,
        )

        assert channel.channel_type == "in_app"
        assert channel.name == "In-App"
        assert channel.is_enabled is True

    def test_notification_preference_model(self):
        """NotificationPreference model can be instantiated."""
        from runner.db.models import NotificationPreference, NotificationType

        user_id = uuid4()
        workspace_id = uuid4()
        channel_id = uuid4()

        pref = NotificationPreference(
            user_id=user_id,
            workspace_id=workspace_id,
            channel_id=channel_id,
            notification_type=NotificationType.APPROVAL_REQUESTED.value,
            is_enabled=True,
        )

        assert pref.user_id == user_id
        assert pref.notification_type == "approval_requested"
        assert pref.is_enabled is True

    def test_notification_model(self):
        """Notification model can be instantiated."""
        from runner.db.models import Notification, NotificationType, NotificationPriority

        user_id = uuid4()
        workspace_id = uuid4()
        actor_id = uuid4()

        notification = Notification(
            user_id=user_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            notification_type=NotificationType.APPROVAL_REQUESTED.value,
            title="Approval Required",
            message="Your post needs approval",
            priority=NotificationPriority.NORMAL.value,
        )

        assert notification.user_id == user_id
        assert notification.notification_type == "approval_requested"
        assert notification.is_read is False
        assert notification.is_dismissed is False


class TestNotificationService:
    """Tests for NotificationService."""

    def test_notification_service_instantiation(self):
        """NotificationService can be instantiated."""
        from api.services import NotificationService

        service = NotificationService()
        assert service is not None

    def test_notification_service_error_classes(self):
        """Service error classes exist."""
        from api.services import (
            NotificationService,
            NotificationServiceError,
            NotificationNotFoundError,
            ChannelNotFoundError,
        )

        # Errors should be proper exception subclasses
        assert issubclass(NotificationNotFoundError, NotificationServiceError)
        assert issubclass(ChannelNotFoundError, NotificationServiceError)


class TestNotificationRoutes:
    """Tests for notification API routes."""

    def test_notification_response_model(self):
        """NotificationResponse model structure."""
        from api.routes.v1.notifications import NotificationResponse

        notification_id = uuid4()
        now = datetime.utcnow()

        response = NotificationResponse(
            id=notification_id,
            notification_type="approval_requested",
            title="Approval Required",
            message="Your post needs approval",
            priority="normal",
            resource_type="post",
            resource_id=uuid4(),
            actor_id=uuid4(),
            is_read=False,
            read_at=None,
            is_dismissed=False,
            dismissed_at=None,
            created_at=now,
        )

        assert response.id == notification_id
        assert response.notification_type == "approval_requested"
        assert response.is_read is False

    def test_notification_list_response_model(self):
        """NotificationListResponse model structure."""
        from api.routes.v1.notifications import NotificationListResponse, NotificationResponse

        now = datetime.utcnow()
        notifications = [
            NotificationResponse(
                id=uuid4(),
                notification_type="approval_requested",
                title="Test",
                message="Test message",
                priority="normal",
                resource_type=None,
                resource_id=None,
                actor_id=None,
                is_read=False,
                read_at=None,
                is_dismissed=False,
                dismissed_at=None,
                created_at=now,
            )
        ]

        response = NotificationListResponse(
            notifications=notifications,
            unread_count=1,
            total=1,
        )

        assert response.unread_count == 1
        assert len(response.notifications) == 1

    def test_mark_read_request_model(self):
        """MarkReadRequest model structure."""
        from api.routes.v1.notifications import MarkReadRequest

        # Mark specific notifications
        req = MarkReadRequest(notification_ids=[uuid4(), uuid4()])
        assert len(req.notification_ids) == 2
        assert req.mark_all is False

        # Mark all notifications
        req = MarkReadRequest(mark_all=True)
        assert req.mark_all is True
        assert len(req.notification_ids) == 0

    def test_bulk_update_preferences_request(self):
        """BulkUpdatePreferencesRequest model structure."""
        from api.routes.v1.notifications import (
            BulkUpdatePreferencesRequest,
            UpdatePreferenceRequest,
        )

        channel_id = uuid4()
        req = BulkUpdatePreferencesRequest(
            preferences=[
                UpdatePreferenceRequest(
                    channel_id=channel_id,
                    notification_type="approval_requested",
                    is_enabled=True,
                ),
                UpdatePreferenceRequest(
                    channel_id=channel_id,
                    notification_type="approval_approved",
                    is_enabled=False,
                ),
            ]
        )

        assert len(req.preferences) == 2
        assert req.preferences[0].is_enabled is True
        assert req.preferences[1].is_enabled is False

    def test_unread_count_response(self):
        """UnreadCountResponse model structure."""
        from api.routes.v1.notifications import UnreadCountResponse

        response = UnreadCountResponse(count=5)
        assert response.count == 5

    def test_notification_channel_response(self):
        """NotificationChannelResponse model structure."""
        from api.routes.v1.notifications import NotificationChannelResponse

        channel_id = uuid4()
        now = datetime.utcnow()

        response = NotificationChannelResponse(
            id=channel_id,
            channel_type="in_app",
            name="In-App",
            description="In-app notifications",
            is_enabled=True,
            created_at=now,
        )

        assert response.id == channel_id
        assert response.channel_type == "in_app"
        assert response.is_enabled is True


class TestNotificationIntegration:
    """Integration tests for notification system."""

    def test_notification_models_import_from_init(self):
        """All notification models can be imported from __init__."""
        from runner.db.models import (
            NotificationChannelType,
            NotificationType,
            NotificationPriority,
            NotificationChannel,
            NotificationChannelCreate,
            NotificationChannelRead,
            NotificationPreference,
            NotificationPreferenceCreate,
            NotificationPreferenceRead,
            Notification,
            NotificationCreate,
            NotificationRead,
        )

        # All should be importable
        assert NotificationChannelType is not None
        assert NotificationType is not None
        assert NotificationPriority is not None
        assert NotificationChannel is not None
        assert NotificationPreference is not None
        assert Notification is not None

    def test_service_import_from_init(self):
        """Notification service can be imported from __init__."""
        from api.services import (
            NotificationService,
            NotificationServiceError,
            NotificationNotFoundError,
            ChannelNotFoundError,
        )

        assert NotificationService is not None
        assert NotificationServiceError is not None
        assert NotificationNotFoundError is not None
        assert ChannelNotFoundError is not None

    def test_router_import_from_init(self):
        """Notification router can be imported from __init__."""
        from api.routes.v1 import notifications_router

        assert notifications_router is not None
