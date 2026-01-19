"""API routes for platform management."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.content_service import ContentService
from runner.content.models import PlatformResponse

router = APIRouter(prefix="/platforms", tags=["platforms"])
content_service = ContentService()


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
def create_platform(request: CreatePlatformRequest):
    """Create a new platform for a user."""
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
def get_platforms(user_id: UUID):
    """Get all platforms for a user."""
    return content_service.get_platforms(user_id)


@router.get("/{platform_id}", response_model=PlatformResponse)
def get_platform(platform_id: UUID):
    """Get a single platform."""
    platform = content_service.get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    return platform


@router.put("/{platform_id}")
def update_platform(platform_id: UUID, request: UpdatePlatformRequest):
    """Update platform fields."""
    # Verify platform exists
    platform = content_service.get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    content_service.update_platform(platform_id, **updates)
    return {"status": "updated"}


@router.delete("/{platform_id}")
def delete_platform(platform_id: UUID):
    """Delete a platform."""
    platform = content_service.get_platform(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    content_service.delete_platform(platform_id)
    return {"status": "deleted"}
