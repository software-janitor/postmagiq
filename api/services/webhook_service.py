"""Webhook service for managing webhook registrations and deliveries.

Provides:
- Webhook registration and management
- Event triggering and delivery
- Retry handling
"""

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from sqlmodel import Session, select

from runner.db.models import (
    Webhook,
    WebhookStatus,
    WebhookDelivery,
    DeliveryStatus,
)


class WebhookServiceError(Exception):
    """Base exception for webhook service errors."""

    pass


class WebhookNotFoundError(WebhookServiceError):
    """Raised when a webhook is not found."""

    pass


class DeliveryNotFoundError(WebhookServiceError):
    """Raised when a delivery is not found."""

    pass


class WebhookService:
    """Service for managing webhooks and deliveries."""

    # ==========================================================================
    # Webhook Management
    # ==========================================================================

    def create_webhook(
        self,
        session: Session,
        workspace_id: UUID,
        created_by_id: UUID,
        name: str,
        url: str,
        events: list[str],
        description: Optional[str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        retry_delay_seconds: int = 60,
        headers: Optional[dict[str, str]] = None,
    ) -> tuple[Webhook, str]:
        """Create a new webhook.

        Returns:
            tuple: (Webhook model, plaintext secret)
            The secret is only returned once at creation.
        """
        # Generate signing secret
        secret, prefix, secret_hash = Webhook.generate_secret()

        webhook = Webhook(
            workspace_id=workspace_id,
            created_by_id=created_by_id,
            name=name,
            description=description,
            url=url,
            events=",".join(events),
            secret_hash=secret_hash,
            secret_prefix=prefix,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            headers=json.dumps(headers) if headers else None,
        )

        session.add(webhook)
        session.commit()
        session.refresh(webhook)

        return webhook, secret

    def get_workspace_webhooks(
        self,
        session: Session,
        workspace_id: UUID,
        include_disabled: bool = False,
    ) -> list[Webhook]:
        """Get all webhooks for a workspace."""
        stmt = select(Webhook).where(Webhook.workspace_id == workspace_id)

        if not include_disabled:
            stmt = stmt.where(Webhook.status != WebhookStatus.DISABLED.value)

        stmt = stmt.order_by(Webhook.created_at.desc())

        return list(session.exec(stmt).all())

    def get_webhook(
        self,
        session: Session,
        webhook_id: UUID,
        workspace_id: UUID,
    ) -> Webhook:
        """Get a specific webhook."""
        webhook = session.get(Webhook, webhook_id)

        if not webhook or webhook.workspace_id != workspace_id:
            raise WebhookNotFoundError(f"Webhook {webhook_id} not found")

        return webhook

    def update_webhook(
        self,
        session: Session,
        webhook_id: UUID,
        workspace_id: UUID,
        **updates,
    ) -> Webhook:
        """Update a webhook."""
        webhook = self.get_webhook(session, webhook_id, workspace_id)

        allowed_fields = {
            "name",
            "description",
            "url",
            "events",
            "status",
            "timeout_seconds",
            "max_retries",
            "retry_delay_seconds",
            "headers",
        }

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                if field == "events" and isinstance(value, list):
                    value = ",".join(value)
                elif field == "headers" and isinstance(value, dict):
                    value = json.dumps(value)
                setattr(webhook, field, value)

        session.add(webhook)
        session.commit()
        session.refresh(webhook)

        return webhook

    def delete_webhook(
        self,
        session: Session,
        webhook_id: UUID,
        workspace_id: UUID,
    ) -> bool:
        """Delete a webhook (soft delete by disabling)."""
        webhook = self.get_webhook(session, webhook_id, workspace_id)

        webhook.status = WebhookStatus.DISABLED.value
        session.add(webhook)
        session.commit()

        return True

    def rotate_secret(
        self,
        session: Session,
        webhook_id: UUID,
        workspace_id: UUID,
    ) -> tuple[Webhook, str]:
        """Rotate the webhook signing secret.

        Returns:
            tuple: (Webhook model, new plaintext secret)
        """
        webhook = self.get_webhook(session, webhook_id, workspace_id)

        secret, prefix, secret_hash = Webhook.generate_secret()
        webhook.secret_hash = secret_hash
        webhook.secret_prefix = prefix

        session.add(webhook)
        session.commit()
        session.refresh(webhook)

        return webhook, secret

    # ==========================================================================
    # Event Triggering
    # ==========================================================================

    def trigger_event(
        self,
        session: Session,
        workspace_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
    ) -> list[WebhookDelivery]:
        """Trigger an event and create delivery records for all matching webhooks.

        Returns:
            list: Created WebhookDelivery records
        """
        # Find all active webhooks for this workspace that subscribe to this event
        webhooks = session.exec(
            select(Webhook).where(
                Webhook.workspace_id == workspace_id,
                Webhook.status == WebhookStatus.ACTIVE.value,
            )
        ).all()

        deliveries = []
        event_id = str(uuid4())

        for webhook in webhooks:
            # Check if webhook subscribes to this event
            subscribed_events = set(
                e.strip() for e in webhook.events.split(",") if e.strip()
            )

            if event_type not in subscribed_events and "*" not in subscribed_events:
                continue

            # Create delivery record
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                workspace_id=workspace_id,
                event_type=event_type,
                event_id=event_id,
                payload=json.dumps(payload),
                status=DeliveryStatus.PENDING.value,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            session.add(delivery)
            deliveries.append(delivery)

        session.commit()

        # Refresh all deliveries
        for delivery in deliveries:
            session.refresh(delivery)

        return deliveries

    async def deliver_webhook(
        self,
        session: Session,
        delivery_id: UUID,
    ) -> WebhookDelivery:
        """Attempt to deliver a webhook.

        This is an async function that should be called from a background task.
        """
        delivery = session.get(WebhookDelivery, delivery_id)
        if not delivery:
            raise DeliveryNotFoundError(f"Delivery {delivery_id} not found")

        webhook = session.get(Webhook, delivery.webhook_id)
        if not webhook:
            delivery.status = DeliveryStatus.FAILED.value
            delivery.error_message = "Webhook not found"
            session.add(delivery)
            session.commit()
            return delivery

        # Prepare payload
        payload_data = json.loads(delivery.payload)
        timestamp = datetime.utcnow().isoformat()

        # Sign payload
        signature = self._sign_payload(
            webhook.secret_hash,
            timestamp,
            delivery.payload,
        )

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery": str(delivery.id),
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": timestamp,
        }

        # Add custom headers if configured
        if webhook.headers:
            custom_headers = json.loads(webhook.headers)
            headers.update(custom_headers)

        start_time = datetime.utcnow()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    json=payload_data,
                    headers=headers,
                    timeout=webhook.timeout_seconds,
                )

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            delivery.response_status_code = response.status_code
            delivery.response_body = response.text[:10000]  # Limit response size
            delivery.response_headers = json.dumps(dict(response.headers))
            delivery.delivered_at = datetime.utcnow()
            delivery.duration_ms = duration_ms

            if 200 <= response.status_code < 300:
                delivery.status = DeliveryStatus.SUCCESS.value
                webhook.successful_deliveries += 1
                webhook.last_success_at = datetime.utcnow()
            else:
                self._handle_failure(
                    session, delivery, webhook, f"HTTP {response.status_code}"
                )

        except httpx.TimeoutException:
            self._handle_failure(session, delivery, webhook, "Request timed out")
        except httpx.RequestError as e:
            self._handle_failure(session, delivery, webhook, str(e))
        except Exception as e:
            self._handle_failure(
                session, delivery, webhook, f"Unexpected error: {str(e)}"
            )

        # Update webhook stats
        webhook.total_deliveries += 1
        webhook.last_delivery_at = datetime.utcnow()

        session.add(delivery)
        session.add(webhook)
        session.commit()
        session.refresh(delivery)

        return delivery

    def _handle_failure(
        self,
        session: Session,
        delivery: WebhookDelivery,
        webhook: Webhook,
        error_message: str,
    ) -> None:
        """Handle a failed delivery attempt."""
        delivery.attempt_number += 1
        delivery.error_message = error_message

        if delivery.attempt_number < webhook.max_retries:
            delivery.status = DeliveryStatus.RETRYING.value
            delivery.next_retry_at = datetime.utcnow() + timedelta(
                seconds=webhook.retry_delay_seconds * delivery.attempt_number
            )
        else:
            delivery.status = DeliveryStatus.FAILED.value
            webhook.failed_deliveries += 1
            webhook.last_failure_at = datetime.utcnow()

    def _sign_payload(
        self,
        secret_hash: str,
        timestamp: str,
        payload: str,
    ) -> str:
        """Create HMAC signature for webhook payload."""
        message = f"{timestamp}.{payload}".encode()
        signature = hmac.new(
            secret_hash.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={signature}"

    # ==========================================================================
    # Delivery Management
    # ==========================================================================

    def get_deliveries(
        self,
        session: Session,
        workspace_id: UUID,
        webhook_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[WebhookDelivery]:
        """Get delivery records."""
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.workspace_id == workspace_id
        )

        if webhook_id:
            stmt = stmt.where(WebhookDelivery.webhook_id == webhook_id)

        if status:
            stmt = stmt.where(WebhookDelivery.status == status)

        stmt = stmt.order_by(WebhookDelivery.created_at.desc()).limit(limit)

        return list(session.exec(stmt).all())

    def retry_delivery(
        self,
        session: Session,
        delivery_id: UUID,
        workspace_id: UUID,
    ) -> WebhookDelivery:
        """Manually retry a failed delivery."""
        delivery = session.get(WebhookDelivery, delivery_id)

        if not delivery or delivery.workspace_id != workspace_id:
            raise DeliveryNotFoundError(f"Delivery {delivery_id} not found")

        if delivery.status not in (
            DeliveryStatus.FAILED.value,
            DeliveryStatus.RETRYING.value,
        ):
            raise WebhookServiceError("Can only retry failed or retrying deliveries")

        # Reset for retry
        delivery.status = DeliveryStatus.PENDING.value
        delivery.attempt_number += 1
        delivery.next_retry_at = None
        delivery.error_message = None

        session.add(delivery)
        session.commit()
        session.refresh(delivery)

        return delivery

    def get_pending_retries(
        self,
        session: Session,
    ) -> list[WebhookDelivery]:
        """Get deliveries that are ready to be retried."""
        return list(
            session.exec(
                select(WebhookDelivery).where(
                    WebhookDelivery.status == DeliveryStatus.RETRYING.value,
                    WebhookDelivery.next_retry_at <= datetime.utcnow(),
                )
            ).all()
        )
