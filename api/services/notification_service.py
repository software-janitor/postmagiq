"""Notification service for managing notifications and preferences.

Provides:
- Sending notifications to users
- Managing notification preferences
- Marking notifications as read
- Counting unread notifications
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, func

from runner.db.models.notification import (
    NotificationChannelType,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationPreference,
    Notification,
)


class NotificationServiceError(Exception):
    """Base exception for notification service errors."""
    pass


class NotificationNotFoundError(NotificationServiceError):
    """Raised when notification is not found."""
    pass


class ChannelNotFoundError(NotificationServiceError):
    """Raised when notification channel is not found."""
    pass


class NotificationService:
    """Service for managing notifications and preferences."""

    # ==========================================================================
    # Notification Channels
    # ==========================================================================

    def get_channels(
        self,
        session: Session,
        enabled_only: bool = True,
    ) -> list[NotificationChannel]:
        """Get all available notification channels."""
        stmt = select(NotificationChannel)
        if enabled_only:
            stmt = stmt.where(NotificationChannel.is_enabled == True)
        stmt = stmt.order_by(NotificationChannel.name)
        return list(session.exec(stmt).all())

    def get_channel(
        self,
        session: Session,
        channel_id: UUID,
    ) -> NotificationChannel:
        """Get a notification channel by ID."""
        channel = session.get(NotificationChannel, channel_id)
        if not channel:
            raise ChannelNotFoundError(f"Channel {channel_id} not found")
        return channel

    def ensure_default_channels(
        self,
        session: Session,
    ) -> list[NotificationChannel]:
        """Create default notification channels if none exist."""
        existing = self.get_channels(session, enabled_only=False)
        if existing:
            return existing

        default_channels = [
            {
                "channel_type": NotificationChannelType.IN_APP.value,
                "name": "In-App",
                "description": "Notifications shown in the application",
                "is_enabled": True,
            },
            {
                "channel_type": NotificationChannelType.EMAIL.value,
                "name": "Email",
                "description": "Notifications sent via email",
                "is_enabled": True,
            },
        ]

        channels = []
        for channel_data in default_channels:
            channel = NotificationChannel(**channel_data)
            session.add(channel)
            channels.append(channel)

        session.commit()
        for channel in channels:
            session.refresh(channel)

        return channels

    # ==========================================================================
    # Notification Preferences
    # ==========================================================================

    def get_user_preferences(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
    ) -> list[NotificationPreference]:
        """Get all notification preferences for a user in a workspace."""
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.workspace_id == workspace_id,
        )
        return list(session.exec(stmt).all())

    def get_preference(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
        channel_id: UUID,
        notification_type: str,
    ) -> Optional[NotificationPreference]:
        """Get a specific notification preference."""
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.workspace_id == workspace_id,
            NotificationPreference.channel_id == channel_id,
            NotificationPreference.notification_type == notification_type,
        )
        return session.exec(stmt).first()

    def set_preference(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
        channel_id: UUID,
        notification_type: str,
        is_enabled: bool,
    ) -> NotificationPreference:
        """Set a notification preference (create or update)."""
        # Verify channel exists
        channel = session.get(NotificationChannel, channel_id)
        if not channel:
            raise ChannelNotFoundError(f"Channel {channel_id} not found")

        # Check for existing preference
        existing = self.get_preference(
            session, user_id, workspace_id, channel_id, notification_type
        )

        if existing:
            existing.is_enabled = is_enabled
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        else:
            pref = NotificationPreference(
                user_id=user_id,
                workspace_id=workspace_id,
                channel_id=channel_id,
                notification_type=notification_type,
                is_enabled=is_enabled,
            )
            session.add(pref)
            session.commit()
            session.refresh(pref)
            return pref

    def set_bulk_preferences(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
        preferences: list[dict],
    ) -> list[NotificationPreference]:
        """Set multiple preferences at once.

        Args:
            preferences: List of dicts with channel_id, notification_type, is_enabled
        """
        results = []
        for pref_data in preferences:
            pref = self.set_preference(
                session,
                user_id,
                workspace_id,
                pref_data["channel_id"],
                pref_data["notification_type"],
                pref_data["is_enabled"],
            )
            results.append(pref)
        return results

    def is_notification_enabled(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
        channel_id: UUID,
        notification_type: str,
    ) -> bool:
        """Check if a notification type is enabled for user/channel.

        Returns True by default if no preference is set.
        """
        pref = self.get_preference(
            session, user_id, workspace_id, channel_id, notification_type
        )
        return pref.is_enabled if pref else True

    def ensure_default_preferences(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
    ) -> list[NotificationPreference]:
        """Create default preferences for a user if none exist."""
        existing = self.get_user_preferences(session, user_id, workspace_id)
        if existing:
            return existing

        channels = self.ensure_default_channels(session)
        in_app_channel = next(
            (c for c in channels if c.channel_type == NotificationChannelType.IN_APP.value),
            None
        )

        if not in_app_channel:
            return []

        # Enable all notification types for in-app by default
        preferences = []
        for notification_type in NotificationType:
            pref = NotificationPreference(
                user_id=user_id,
                workspace_id=workspace_id,
                channel_id=in_app_channel.id,
                notification_type=notification_type.value,
                is_enabled=True,
            )
            session.add(pref)
            preferences.append(pref)

        session.commit()
        for pref in preferences:
            session.refresh(pref)

        return preferences

    # ==========================================================================
    # Sending Notifications
    # ==========================================================================

    def send_notification(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        actor_id: Optional[UUID] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        data: Optional[dict] = None,
    ) -> Notification:
        """Send a notification to a user.

        Creates the notification and handles delivery via enabled channels.
        """
        # Get enabled channels for this notification type
        channels = self.ensure_default_channels(session)
        delivered_channels = []

        for channel in channels:
            if channel.is_enabled and self.is_notification_enabled(
                session, user_id, workspace_id, channel.id, notification_type.value
            ):
                delivered_channels.append(channel.channel_type)

                # For email channel, we would queue email delivery here
                # For now, we just track that it should be delivered
                if channel.channel_type == NotificationChannelType.EMAIL.value:
                    # TODO: Queue email delivery
                    pass

        # Create the notification record
        notification = Notification(
            user_id=user_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            notification_type=notification_type.value,
            title=title,
            message=message,
            priority=priority.value,
            resource_type=resource_type,
            resource_id=resource_id,
            data=json.dumps(data) if data else None,
            delivered_via=json.dumps(delivered_channels) if delivered_channels else None,
            delivered_at=datetime.utcnow() if delivered_channels else None,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        return notification

    def send_to_multiple_users(
        self,
        session: Session,
        user_ids: list[UUID],
        workspace_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        actor_id: Optional[UUID] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        data: Optional[dict] = None,
    ) -> list[Notification]:
        """Send the same notification to multiple users."""
        notifications = []
        for user_id in user_ids:
            notification = self.send_notification(
                session,
                user_id,
                workspace_id,
                notification_type,
                title,
                message,
                actor_id,
                priority,
                resource_type,
                resource_id,
                data,
            )
            notifications.append(notification)
        return notifications

    # ==========================================================================
    # Reading Notifications
    # ==========================================================================

    def get_notifications(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
        unread_only: bool = False,
        include_dismissed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Get notifications for a user."""
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.workspace_id == workspace_id,
        )

        if unread_only:
            stmt = stmt.where(Notification.is_read == False)

        if not include_dismissed:
            stmt = stmt.where(Notification.is_dismissed == False)

        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)

        return list(session.exec(stmt).all())

    def get_notification(
        self,
        session: Session,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification:
        """Get a specific notification."""
        notification = session.get(Notification, notification_id)
        if not notification or notification.user_id != user_id:
            raise NotificationNotFoundError(f"Notification {notification_id} not found")
        return notification

    def get_unread_count(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Get count of unread notifications for a user."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.workspace_id == workspace_id,
            Notification.is_read == False,
            Notification.is_dismissed == False,
        )
        result = session.exec(stmt).one()
        return result

    # ==========================================================================
    # Marking Notifications
    # ==========================================================================

    def mark_as_read(
        self,
        session: Session,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification:
        """Mark a notification as read."""
        notification = self.get_notification(session, notification_id, user_id)

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            session.add(notification)
            session.commit()
            session.refresh(notification)

        return notification

    def mark_multiple_as_read(
        self,
        session: Session,
        notification_ids: list[UUID],
        user_id: UUID,
    ) -> list[Notification]:
        """Mark multiple notifications as read."""
        notifications = []
        for notification_id in notification_ids:
            try:
                notification = self.mark_as_read(session, notification_id, user_id)
                notifications.append(notification)
            except NotificationNotFoundError:
                continue
        return notifications

    def mark_all_as_read(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Mark all unread notifications as read. Returns count of marked."""
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.workspace_id == workspace_id,
            Notification.is_read == False,
        )
        notifications = session.exec(stmt).all()

        count = 0
        now = datetime.utcnow()
        for notification in notifications:
            notification.is_read = True
            notification.read_at = now
            session.add(notification)
            count += 1

        session.commit()
        return count

    def dismiss(
        self,
        session: Session,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification:
        """Dismiss a notification (hide it from the list)."""
        notification = self.get_notification(session, notification_id, user_id)

        if not notification.is_dismissed:
            notification.is_dismissed = True
            notification.dismissed_at = datetime.utcnow()
            session.add(notification)
            session.commit()
            session.refresh(notification)

        return notification

    def dismiss_all(
        self,
        session: Session,
        user_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Dismiss all notifications. Returns count of dismissed."""
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.workspace_id == workspace_id,
            Notification.is_dismissed == False,
        )
        notifications = session.exec(stmt).all()

        count = 0
        now = datetime.utcnow()
        for notification in notifications:
            notification.is_dismissed = True
            notification.dismissed_at = now
            session.add(notification)
            count += 1

        session.commit()
        return count
