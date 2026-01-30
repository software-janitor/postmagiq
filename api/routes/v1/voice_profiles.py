"""Workspace-scoped voice profile routes.

All voice profile operations are scoped to a workspace via /api/v1/w/{workspace_id}/...
This ensures multi-tenancy by requiring workspace context for all queries.

Presets (is_preset=True) are included in list results but cannot be deleted.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select, or_

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceCtx,
    WorkspaceContext,
    require_workspace_scope,
)
from runner.db.engine import get_session_dependency
from runner.db.models import VoiceProfile


router = APIRouter(
    prefix="/v1/w/{workspace_id}/voice-profiles", tags=["voice-profiles"]
)


# =============================================================================
# Request/Response Models
# =============================================================================


class VoiceProfileResponse(BaseModel):
    """Voice profile data for API responses."""

    id: UUID
    workspace_id: Optional[UUID]
    name: str
    slug: str
    description: Optional[str]
    is_preset: bool
    tone_description: Optional[str]
    signature_phrases: Optional[str]
    word_choices: Optional[str]
    example_excerpts: Optional[str]
    avoid_patterns: Optional[str]


class CreateVoiceProfileRequest(BaseModel):
    """Request to create a voice profile."""

    name: str
    slug: str
    description: Optional[str] = None
    tone_description: Optional[str] = None
    signature_phrases: Optional[str] = None
    word_choices: Optional[str] = None
    example_excerpts: Optional[str] = None
    avoid_patterns: Optional[str] = None


class UpdateVoiceProfileRequest(BaseModel):
    """Request to update a voice profile."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    tone_description: Optional[str] = None
    signature_phrases: Optional[str] = None
    word_choices: Optional[str] = None
    example_excerpts: Optional[str] = None
    avoid_patterns: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def _to_response(profile: VoiceProfile) -> VoiceProfileResponse:
    """Convert a VoiceProfile model to response."""
    return VoiceProfileResponse(
        id=profile.id,
        workspace_id=profile.workspace_id,
        name=profile.name,
        slug=profile.slug,
        description=profile.description,
        is_preset=profile.is_preset,
        tone_description=profile.tone_description,
        signature_phrases=profile.signature_phrases,
        word_choices=profile.word_choices,
        example_excerpts=profile.example_excerpts,
        avoid_patterns=profile.avoid_patterns,
    )


# =============================================================================
# Voice Profile Endpoints
# =============================================================================


@router.get("", response_model=list[VoiceProfileResponse])
async def list_voice_profiles(
    ctx: WorkspaceCtx,
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """List all voice profiles in the workspace.

    Includes:
    - Workspace-specific profiles
    - System presets (is_preset=True)
    """
    # Get workspace profiles + system presets (is_preset=True with workspace_id=None)
    statement = select(VoiceProfile).where(
        or_(
            VoiceProfile.workspace_id == ctx.workspace_id,
            VoiceProfile.is_preset,
        )
    )
    profiles = session.exec(statement).all()

    return [_to_response(p) for p in profiles]


@router.get("/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice_profile(
    profile_id: UUID,
    ctx: WorkspaceCtx,
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get a specific voice profile.

    Accessible if:
    - Profile belongs to the workspace
    - Profile is a system preset
    """
    profile = session.get(VoiceProfile, profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found",
        )

    # Check access: workspace match or system preset
    if profile.workspace_id != ctx.workspace_id and not profile.is_preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found",
        )

    return _to_response(profile)


@router.post(
    "", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_voice_profile(
    request: CreateVoiceProfileRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Create a new voice profile.

    Requires strategy:write scope.
    New profiles are workspace-scoped (not system presets).
    """
    profile = VoiceProfile(
        workspace_id=ctx.workspace_id,
        name=request.name,
        slug=request.slug,
        description=request.description,
        tone_description=request.tone_description,
        signature_phrases=request.signature_phrases,
        word_choices=request.word_choices,
        example_excerpts=request.example_excerpts,
        avoid_patterns=request.avoid_patterns,
        is_preset=False,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)

    return _to_response(profile)


@router.put("/{profile_id}", response_model=VoiceProfileResponse)
async def update_voice_profile(
    profile_id: UUID,
    request: UpdateVoiceProfileRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Update a voice profile.

    Requires strategy:write scope.
    Only workspace-owned profiles can be updated (not system presets).
    """
    profile = session.get(VoiceProfile, profile_id)

    if not profile or profile.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found",
        )

    if profile.is_preset:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system preset profiles",
        )

    # Apply updates
    updates = request.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)

    session.add(profile)
    session.commit()
    session.refresh(profile)

    return _to_response(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_profile(
    profile_id: UUID,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Delete a voice profile.

    Requires strategy:write scope.
    Only workspace-owned profiles can be deleted (not system presets).
    """
    profile = session.get(VoiceProfile, profile_id)

    if not profile or profile.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found",
        )

    if profile.is_preset:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system preset profiles",
        )

    session.delete(profile)
    session.commit()
