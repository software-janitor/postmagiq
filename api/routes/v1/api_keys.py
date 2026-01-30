"""API Key routes for managing programmatic access.

Provides endpoints for:
- Creating and listing API keys
- Revoking keys
- Updating key metadata
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceContext,
    require_workspace_scope,
)
from api.services import (
    APIKeyService,
    APIKeyServiceError,
    KeyNotFoundError,
)
from runner.db.engine import get_session_dependency


router = APIRouter(prefix="/v1/w/{workspace_id}/api-keys", tags=["api-keys"])

api_key_service = APIKeyService()


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateAPIKeyRequest(BaseModel):
    """Request to create an API key."""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: Optional[list[str]] = None
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    rate_limit_per_day: int = Field(default=10000, ge=1, le=1000000)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)


class UpdateAPIKeyRequest(BaseModel):
    """Request to update an API key."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: Optional[list[str]] = None
    rate_limit_per_minute: Optional[int] = Field(default=None, ge=1, le=1000)
    rate_limit_per_day: Optional[int] = Field(default=None, ge=1, le=1000000)


class APIKeyResponse(BaseModel):
    """Response model for API keys (without sensitive fields)."""

    id: UUID
    workspace_id: UUID
    created_by_id: UUID
    name: str
    description: Optional[str]
    key_prefix: str
    scopes: str
    rate_limit_per_minute: int
    rate_limit_per_day: int
    status: str
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    total_requests: int
    created_at: datetime


class APIKeyCreatedResponse(APIKeyResponse):
    """Response when creating an API key (includes the plaintext key)."""

    key: str  # The full key - only shown once at creation


# =============================================================================
# API Key Management
# =============================================================================


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
    include_revoked: bool = False,
):
    """List API keys for the workspace. Requires admin scope."""
    keys = api_key_service.get_workspace_keys(
        session, ctx.workspace_id, include_revoked
    )
    return [
        APIKeyResponse(
            id=k.id,
            workspace_id=k.workspace_id,
            created_by_id=k.created_by_id,
            name=k.name,
            description=k.description,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            rate_limit_per_minute=k.rate_limit_per_minute,
            rate_limit_per_day=k.rate_limit_per_day,
            status=k.status,
            expires_at=k.expires_at,
            last_used_at=k.last_used_at,
            total_requests=k.total_requests,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post(
    "", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Create a new API key. Requires admin scope.

    The full key is only returned once at creation. Store it securely.
    """
    api_key, plaintext_key = api_key_service.create_key(
        session,
        ctx.workspace_id,
        ctx.user_id,
        name=request.name,
        description=request.description,
        scopes=request.scopes,
        rate_limit_per_minute=request.rate_limit_per_minute,
        rate_limit_per_day=request.rate_limit_per_day,
        expires_in_days=request.expires_in_days,
    )
    return APIKeyCreatedResponse(
        id=api_key.id,
        workspace_id=api_key.workspace_id,
        created_by_id=api_key.created_by_id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        key=plaintext_key,
        scopes=api_key.scopes,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        rate_limit_per_day=api_key.rate_limit_per_day,
        status=api_key.status,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        total_requests=api_key.total_requests,
        created_at=api_key.created_at,
    )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get a specific API key. Requires admin scope."""
    try:
        api_key = api_key_service.get_key_by_id(session, key_id, ctx.workspace_id)
        return APIKeyResponse(
            id=api_key.id,
            workspace_id=api_key.workspace_id,
            created_by_id=api_key.created_by_id,
            name=api_key.name,
            description=api_key.description,
            key_prefix=api_key.key_prefix,
            scopes=api_key.scopes,
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            rate_limit_per_day=api_key.rate_limit_per_day,
            status=api_key.status,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            total_requests=api_key.total_requests,
            created_at=api_key.created_at,
        )
    except KeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: UUID,
    request: UpdateAPIKeyRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Update an API key. Requires admin scope."""
    try:
        api_key = api_key_service.update_key(
            session,
            key_id,
            ctx.workspace_id,
            **request.model_dump(exclude_unset=True),
        )
        return APIKeyResponse(
            id=api_key.id,
            workspace_id=api_key.workspace_id,
            created_by_id=api_key.created_by_id,
            name=api_key.name,
            description=api_key.description,
            key_prefix=api_key.key_prefix,
            scopes=api_key.scopes,
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            rate_limit_per_day=api_key.rate_limit_per_day,
            status=api_key.status,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            total_requests=api_key.total_requests,
            created_at=api_key.created_at,
        )
    except KeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Revoke an API key. Requires admin scope."""
    try:
        api_key_service.revoke_key(
            session,
            key_id,
            ctx.workspace_id,
            ctx.user_id,
        )
    except KeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    except APIKeyServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
