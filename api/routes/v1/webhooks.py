"""Webhook routes for managing webhook registrations and deliveries.

Provides endpoints for:
- Registering and managing webhooks
- Viewing delivery history
- Retrying failed deliveries
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceContext,
    require_workspace_scope,
)
from api.services import (
    WebhookService,
    WebhookServiceError,
    WebhookNotFoundError,
    DeliveryNotFoundError,
)
from runner.db.engine import get_session_dependency


router = APIRouter(prefix="/v1/w/{workspace_id}/webhooks", tags=["webhooks"])

webhook_service = WebhookService()


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook."""
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    url: str = Field(min_length=1)
    events: list[str] = Field(min_length=1)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)
    headers: Optional[dict[str, str]] = None


class UpdateWebhookRequest(BaseModel):
    """Request to update a webhook."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    url: Optional[str] = Field(default=None, min_length=1)
    events: Optional[list[str]] = None
    status: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=5, le=120)
    max_retries: Optional[int] = Field(default=None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(default=None, ge=10, le=3600)
    headers: Optional[dict[str, str]] = None


class WebhookResponse(BaseModel):
    """Response model for webhooks."""
    id: UUID
    workspace_id: UUID
    created_by_id: UUID
    name: str
    description: Optional[str]
    url: str
    events: str
    secret_prefix: str
    status: str
    timeout_seconds: int
    max_retries: int
    retry_delay_seconds: int
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_delivery_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    created_at: datetime


class WebhookCreatedResponse(WebhookResponse):
    """Response when creating a webhook (includes the signing secret)."""
    secret: str  # The full secret - only shown once at creation


class WebhookDeliveryResponse(BaseModel):
    """Response model for webhook deliveries."""
    id: UUID
    webhook_id: UUID
    workspace_id: UUID
    event_type: str
    event_id: str
    status: str
    response_status_code: Optional[int]
    delivered_at: Optional[datetime]
    duration_ms: Optional[int]
    attempt_number: int
    next_retry_at: Optional[datetime]
    error_message: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[UUID]
    created_at: datetime


# =============================================================================
# Webhook Management
# =============================================================================


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
    include_disabled: bool = False,
):
    """List webhooks for the workspace. Requires admin scope."""
    webhooks = webhook_service.get_workspace_webhooks(
        session, ctx.workspace_id, include_disabled
    )
    return [
        WebhookResponse(
            id=w.id,
            workspace_id=w.workspace_id,
            created_by_id=w.created_by_id,
            name=w.name,
            description=w.description,
            url=w.url,
            events=w.events,
            secret_prefix=w.secret_prefix,
            status=w.status,
            timeout_seconds=w.timeout_seconds,
            max_retries=w.max_retries,
            retry_delay_seconds=w.retry_delay_seconds,
            total_deliveries=w.total_deliveries,
            successful_deliveries=w.successful_deliveries,
            failed_deliveries=w.failed_deliveries,
            last_delivery_at=w.last_delivery_at,
            last_success_at=w.last_success_at,
            last_failure_at=w.last_failure_at,
            created_at=w.created_at,
        )
        for w in webhooks
    ]


@router.post("", response_model=WebhookCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: CreateWebhookRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Create a new webhook. Requires admin scope.

    The signing secret is only returned once at creation. Store it securely.
    """
    webhook, secret = webhook_service.create_webhook(
        session,
        ctx.workspace_id,
        ctx.user_id,
        name=request.name,
        url=request.url,
        events=request.events,
        description=request.description,
        timeout_seconds=request.timeout_seconds,
        max_retries=request.max_retries,
        retry_delay_seconds=request.retry_delay_seconds,
        headers=request.headers,
    )
    return WebhookCreatedResponse(
        id=webhook.id,
        workspace_id=webhook.workspace_id,
        created_by_id=webhook.created_by_id,
        name=webhook.name,
        description=webhook.description,
        url=webhook.url,
        events=webhook.events,
        secret_prefix=webhook.secret_prefix,
        secret=secret,
        status=webhook.status,
        timeout_seconds=webhook.timeout_seconds,
        max_retries=webhook.max_retries,
        retry_delay_seconds=webhook.retry_delay_seconds,
        total_deliveries=webhook.total_deliveries,
        successful_deliveries=webhook.successful_deliveries,
        failed_deliveries=webhook.failed_deliveries,
        last_delivery_at=webhook.last_delivery_at,
        last_success_at=webhook.last_success_at,
        last_failure_at=webhook.last_failure_at,
        created_at=webhook.created_at,
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get a specific webhook. Requires admin scope."""
    try:
        webhook = webhook_service.get_webhook(session, webhook_id, ctx.workspace_id)
        return WebhookResponse(
            id=webhook.id,
            workspace_id=webhook.workspace_id,
            created_by_id=webhook.created_by_id,
            name=webhook.name,
            description=webhook.description,
            url=webhook.url,
            events=webhook.events,
            secret_prefix=webhook.secret_prefix,
            status=webhook.status,
            timeout_seconds=webhook.timeout_seconds,
            max_retries=webhook.max_retries,
            retry_delay_seconds=webhook.retry_delay_seconds,
            total_deliveries=webhook.total_deliveries,
            successful_deliveries=webhook.successful_deliveries,
            failed_deliveries=webhook.failed_deliveries,
            last_delivery_at=webhook.last_delivery_at,
            last_success_at=webhook.last_success_at,
            last_failure_at=webhook.last_failure_at,
            created_at=webhook.created_at,
        )
    except WebhookNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    request: UpdateWebhookRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Update a webhook. Requires admin scope."""
    try:
        webhook = webhook_service.update_webhook(
            session,
            webhook_id,
            ctx.workspace_id,
            **request.model_dump(exclude_unset=True),
        )
        return WebhookResponse(
            id=webhook.id,
            workspace_id=webhook.workspace_id,
            created_by_id=webhook.created_by_id,
            name=webhook.name,
            description=webhook.description,
            url=webhook.url,
            events=webhook.events,
            secret_prefix=webhook.secret_prefix,
            status=webhook.status,
            timeout_seconds=webhook.timeout_seconds,
            max_retries=webhook.max_retries,
            retry_delay_seconds=webhook.retry_delay_seconds,
            total_deliveries=webhook.total_deliveries,
            successful_deliveries=webhook.successful_deliveries,
            failed_deliveries=webhook.failed_deliveries,
            last_delivery_at=webhook.last_delivery_at,
            last_success_at=webhook.last_success_at,
            last_failure_at=webhook.last_failure_at,
            created_at=webhook.created_at,
        )
    except WebhookNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Delete (disable) a webhook. Requires admin scope."""
    try:
        webhook_service.delete_webhook(session, webhook_id, ctx.workspace_id)
    except WebhookNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")


@router.post("/{webhook_id}/rotate-secret", response_model=WebhookCreatedResponse)
async def rotate_webhook_secret(
    webhook_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Rotate the webhook signing secret. Requires admin scope.

    The new secret is only returned once. Store it securely.
    """
    try:
        webhook, secret = webhook_service.rotate_secret(
            session, webhook_id, ctx.workspace_id
        )
        return WebhookCreatedResponse(
            id=webhook.id,
            workspace_id=webhook.workspace_id,
            created_by_id=webhook.created_by_id,
            name=webhook.name,
            description=webhook.description,
            url=webhook.url,
            events=webhook.events,
            secret_prefix=webhook.secret_prefix,
            secret=secret,
            status=webhook.status,
            timeout_seconds=webhook.timeout_seconds,
            max_retries=webhook.max_retries,
            retry_delay_seconds=webhook.retry_delay_seconds,
            total_deliveries=webhook.total_deliveries,
            successful_deliveries=webhook.successful_deliveries,
            failed_deliveries=webhook.failed_deliveries,
            last_delivery_at=webhook.last_delivery_at,
            last_success_at=webhook.last_success_at,
            last_failure_at=webhook.last_failure_at,
            created_at=webhook.created_at,
        )
    except WebhookNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")


# =============================================================================
# Delivery History
# =============================================================================


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    webhook_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
    status_filter: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """List delivery history for a webhook. Requires admin scope."""
    deliveries = webhook_service.get_deliveries(
        session,
        ctx.workspace_id,
        webhook_id=webhook_id,
        status=status_filter,
        limit=limit,
    )
    return [
        WebhookDeliveryResponse(
            id=d.id,
            webhook_id=d.webhook_id,
            workspace_id=d.workspace_id,
            event_type=d.event_type,
            event_id=d.event_id,
            status=d.status,
            response_status_code=d.response_status_code,
            delivered_at=d.delivered_at,
            duration_ms=d.duration_ms,
            attempt_number=d.attempt_number,
            next_retry_at=d.next_retry_at,
            error_message=d.error_message,
            resource_type=d.resource_type,
            resource_id=d.resource_id,
            created_at=d.created_at,
        )
        for d in deliveries
    ]


@router.get("/deliveries/all", response_model=list[WebhookDeliveryResponse])
async def list_all_deliveries(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
    status_filter: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """List all delivery history for the workspace. Requires admin scope."""
    deliveries = webhook_service.get_deliveries(
        session,
        ctx.workspace_id,
        status=status_filter,
        limit=limit,
    )
    return [
        WebhookDeliveryResponse(
            id=d.id,
            webhook_id=d.webhook_id,
            workspace_id=d.workspace_id,
            event_type=d.event_type,
            event_id=d.event_id,
            status=d.status,
            response_status_code=d.response_status_code,
            delivered_at=d.delivered_at,
            duration_ms=d.duration_ms,
            attempt_number=d.attempt_number,
            next_retry_at=d.next_retry_at,
            error_message=d.error_message,
            resource_type=d.resource_type,
            resource_id=d.resource_id,
            created_at=d.created_at,
        )
        for d in deliveries
    ]


@router.post("/deliveries/{delivery_id}/retry", response_model=WebhookDeliveryResponse)
async def retry_delivery(
    delivery_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Manually retry a failed delivery. Requires admin scope."""
    try:
        delivery = webhook_service.retry_delivery(
            session, delivery_id, ctx.workspace_id
        )
        return WebhookDeliveryResponse(
            id=delivery.id,
            webhook_id=delivery.webhook_id,
            workspace_id=delivery.workspace_id,
            event_type=delivery.event_type,
            event_id=delivery.event_id,
            status=delivery.status,
            response_status_code=delivery.response_status_code,
            delivered_at=delivery.delivered_at,
            duration_ms=delivery.duration_ms,
            attempt_number=delivery.attempt_number,
            next_retry_at=delivery.next_retry_at,
            error_message=delivery.error_message,
            resource_type=delivery.resource_type,
            resource_id=delivery.resource_id,
            created_at=delivery.created_at,
        )
    except DeliveryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    except WebhookServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
