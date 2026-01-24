"""API routes for platform management."""

from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import CurrentUser, get_current_user
from api.services.content_service import ContentService
from runner.content.models import PlatformResponse
from runner.db.models import UserRole

router = APIRouter(prefix="/platforms", tags=["platforms"])
content_service = ContentService()


def _verify_user_access(current_user: CurrentUser, target_user_id: UUID) -> None:
    """Verify user can access the target user's data."""
    is_owner = current_user.user.role == UserRole.owner
    if str(current_user.user_id) != str(target_user_id) and not is_owner:
        raise HTTPException(status_code=404, detail="Resource not found")


# =============================================================================
# Request Models
# =============================================================================


class CreatePlatformRequest(BaseModel):
    """Create a new platform."""
    user_id: UUID
    name: str
    description: Optional[str] = None
    post_format: Optional[str] = None  # "long-form", "short-form", "thread"
    default_word_count: Optional[int] = None
    uses_enemies: bool = True


class UpdatePlatformRequest(BaseModel):
    """Update platform fields."""
    name: Optional[str] = None
    description: Optional[str] = None
    post_format: Optional[str] = None
    default_word_count: Optional[int] = None
    uses_enemies: Optional[bool] = None
    is_active: Optional[bool] = None


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=dict)
def create_platform(
    request: CreatePlatformRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Create a new platform for a user."""
    _verify_user_access(current_user, request.user_id)

    platform_id = content_service.create_platform(
        user_id=request.user_id,
        name=request.name,
        description=request.description,
        post_format=request.post_format,
        default_word_count=request.default_word_count,
        uses_enemies=request.uses_enemies,
    )
    return {"id": platform_id}


@router.get("/user/{user_id}", response_model=list[PlatformResponse])
def get_platforms(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get all platforms for a user."""
    _verify_user_access(current_user, user_id)

    return content_service.get_platforms(user_id)


@router.get("/{platform_id}", response_model=PlatformResponse)
def get_platform(
    platform_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get a single platform."""
    platform = content_service.get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    # Verify ownership
    if platform.user_id:
        _verify_user_access(current_user, platform.user_id)

    return platform


@router.put("/{platform_id}")
def update_platform(
    platform_id: UUID,
    request: UpdatePlatformRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Update platform fields."""
    # Verify platform exists
    platform = content_service.get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    # Verify ownership
    if platform.user_id:
        _verify_user_access(current_user, platform.user_id)

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    content_service.update_platform(platform_id, **updates)
    return {"status": "updated"}


@router.delete("/{platform_id}")
def delete_platform(
    platform_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Delete a platform."""
    platform = content_service.get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    # Verify ownership
    if platform.user_id:
        _verify_user_access(current_user, platform.user_id)

    content_service.delete_platform(platform_id)
    return {"status": "deleted"}
