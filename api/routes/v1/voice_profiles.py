"""Workspace-scoped voice profile routes.

All voice profile operations are scoped to a workspace via /api/v1/w/{workspace_id}/...
This ensures multi-tenancy by requiring workspace context for all queries.

Presets (is_library=True) are included in list results but cannot be deleted.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select, or_

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceCtx,
    WorkspaceContext,
    require_workspace_scope,
)
from runner.db.engine import get_session_dependency
from runner.db.models import VoiceProfile


router = APIRouter(prefix="/v1/w/{workspace_id}/voice-profiles", tags=["voice-profiles"])


# =============================================================================
# Request/Response Models
# =============================================================================


class VoiceProfileResponse(BaseModel):
    """Voice profile data for API responses."""

    id: UUID
    workspace_id: Optional[UUID]
    name: Optional[str]
    tone: Optional[str]
    sentence_patterns: Optional[str]
    vocabulary_level: Optional[str]
    signature_phrases: Optional[str]
    storytelling_style: Optional[str]
    emotional_register: Optional[str]
    is_library: bool
    is_shared: bool
    source_sample_count: int


class CreateVoiceProfileRequest(BaseModel):
    """Request to create a voice profile."""

    name: Optional[str] = None
    tone: Optional[str] = None
    sentence_patterns: Optional[str] = None
    vocabulary_level: Optional[str] = None
    signature_phrases: Optional[str] = None
    storytelling_style: Optional[str] = None
    emotional_register: Optional[str] = None
    raw_analysis: Optional[str] = None


class UpdateVoiceProfileRequest(BaseModel):
    """Request to update a voice profile."""

    name: Optional[str] = None
    tone: Optional[str] = None
    sentence_patterns: Optional[str] = None
    vocabulary_level: Optional[str] = None
    signature_phrases: Optional[str] = None
    storytelling_style: Optional[str] = None
    emotional_register: Optional[str] = None
    raw_analysis: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def _to_response(profile: VoiceProfile) -> VoiceProfileResponse:
    """Convert a VoiceProfile model to response."""
    return VoiceProfileResponse(
        id=profile.id,
        workspace_id=profile.workspace_id,
        name=profile.name,
        tone=profile.tone,
        sentence_patterns=profile.sentence_patterns,
        vocabulary_level=profile.vocabulary_level,
        signature_phrases=profile.signature_phrases,
        storytelling_style=profile.storytelling_style,
        emotional_register=profile.emotional_register,
        is_library=profile.is_library,
        is_shared=profile.is_shared,
        source_sample_count=profile.source_sample_count,
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
    - Library presets (is_library=True, workspace_id=None)
    - Shared profiles (is_shared=True)
    """
    # Get workspace profiles + library presets + shared profiles
    statement = select(VoiceProfile).where(
        or_(
            VoiceProfile.workspace_id == ctx.workspace_id,
            VoiceProfile.is_library == True,
            VoiceProfile.is_shared == True,
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
    - Profile is a library preset
    - Profile is shared
    """
    profile = session.get(VoiceProfile, profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found",
        )

    # Check access: workspace match, library preset, or shared
    if (
        profile.workspace_id != ctx.workspace_id
        and not profile.is_library
        and not profile.is_shared
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found",
        )

    return _to_response(profile)


@router.post("", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_voice_profile(
    request: CreateVoiceProfileRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Create a new voice profile.

    Requires strategy:write scope.
    New profiles are workspace-scoped (not library presets).
    """
    profile = VoiceProfile(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        name=request.name,
        tone=request.tone,
        sentence_patterns=request.sentence_patterns,
        vocabulary_level=request.vocabulary_level,
        signature_phrases=request.signature_phrases,
        storytelling_style=request.storytelling_style,
        emotional_register=request.emotional_register,
        raw_analysis=request.raw_analysis,
        is_library=False,
        is_shared=False,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)

    return _to_response(profile)


@router.put("/{profile_id}", response_model=VoiceProfileResponse)
async def update_voice_profile(
    profile_id: UUID,
    request: UpdateVoiceProfileRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Update a voice profile.

    Requires strategy:write scope.
    Only workspace-owned profiles can be updated (not library presets).
    """
    profile = session.get(VoiceProfile, profile_id)

    if not profile or profile.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found",
        )

    if profile.is_library:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify library preset profiles",
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
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Delete a voice profile.

    Requires strategy:write scope.
    Only workspace-owned profiles can be deleted (not library presets).
    """
    profile = session.get(VoiceProfile, profile_id)

    if not profile or profile.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found",
        )

    if profile.is_library:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete library preset profiles",
        )

    session.delete(profile)
    session.commit()
