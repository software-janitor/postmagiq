"""API routes for voice learning."""

from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import CurrentUser, get_current_user
from api.services.voice_service import VoiceService, WritingSample
from runner.db.models import UserRole

router = APIRouter(prefix="/voice", tags=["voice"])
voice_service = VoiceService()


def _verify_user_access(current_user: CurrentUser, target_user_id: UUID) -> None:
    """Verify user can access the target user's data.

    Users can only access their own data unless they are an owner.
    """
    is_owner = current_user.user.role == UserRole.owner
    if str(current_user.user_id) != str(target_user_id) and not is_owner:
        raise HTTPException(status_code=404, detail="Resource not found")


# =============================================================================
# Request Models
# =============================================================================


class SaveSampleRequest(BaseModel):
    """Save a writing sample."""
    user_id: UUID
    source_type: str  # "prompt" or "upload"
    content: str
    prompt_id: Optional[str] = None
    title: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Request voice analysis."""
    user_id: UUID


# =============================================================================
# Response Models
# =============================================================================


class PromptsResponse(BaseModel):
    """Available voice prompts."""
    prompts: list[dict]


class SampleResponse(BaseModel):
    """Saved sample info."""
    id: str
    word_count: int


class SamplesResponse(BaseModel):
    """User's writing samples."""
    samples: list[dict]
    total_word_count: int
    can_analyze: bool


class AnalysisResponse(BaseModel):
    """Voice analysis result."""
    profile_id: str
    tone: str
    sentence_patterns: dict
    vocabulary_level: str
    signature_phrases: list[str]
    storytelling_style: str
    emotional_register: str
    summary: str


class ProfileResponse(BaseModel):
    """User's voice profile."""
    id: str
    name: str = "Default"
    description: Optional[str] = None
    is_default: bool = False
    tone: Optional[str]
    sentence_patterns: dict
    vocabulary_level: Optional[str]
    signature_phrases: list[str]
    storytelling_style: Optional[str]
    emotional_register: Optional[str]
    created_at: Optional[str] = None


class ProfilesResponse(BaseModel):
    """List of voice profiles."""
    profiles: list[ProfileResponse]


class CloneProfileRequest(BaseModel):
    """Clone a profile."""
    new_name: str


class UpdateProfileRequest(BaseModel):
    """Update profile metadata."""
    name: Optional[str] = None
    description: Optional[str] = None


# =============================================================================
# Prompts
# =============================================================================


@router.get("/prompts", response_model=PromptsResponse)
def get_prompts(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get the 10 voice learning prompts."""
    return PromptsResponse(prompts=VoiceService.get_prompts())


@router.get("/prompts/{prompt_id}")
def get_prompt(
    prompt_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get a specific prompt by ID."""
    prompt = VoiceService.get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


# =============================================================================
# Samples
# =============================================================================


@router.post("/samples", response_model=SampleResponse)
def save_sample(
    request: SaveSampleRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Save a writing sample."""
    _verify_user_access(current_user, request.user_id)

    # Validate word count for prompt samples
    if request.source_type == "prompt":
        is_valid, word_count = VoiceService.validate_sample_word_count(
            request.content, max_words=500
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Sample exceeds 500 word limit ({word_count} words)",
            )

    # Get prompt text if prompt_id provided
    prompt_text = None
    if request.prompt_id:
        prompt = VoiceService.get_prompt_by_id(request.prompt_id)
        if prompt:
            prompt_text = prompt["prompt"]

    sample = WritingSample(
        source_type=request.source_type,
        prompt_id=request.prompt_id,
        prompt_text=prompt_text,
        title=request.title,
        content=request.content,
    )

    sample_id = voice_service.save_sample(request.user_id, sample)
    word_count = len(request.content.split())

    return SampleResponse(id=sample_id, word_count=word_count)


@router.get("/users/{user_id}/samples", response_model=SamplesResponse)
def get_samples(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get all writing samples for a user."""
    _verify_user_access(current_user, user_id)

    samples = voice_service.get_samples(user_id)
    total_words = voice_service.get_total_word_count(user_id)
    can_analyze, _ = voice_service.can_analyze(user_id)

    return SamplesResponse(
        samples=samples,
        total_word_count=total_words,
        can_analyze=can_analyze,
    )


@router.get("/users/{user_id}/samples/status")
def get_sample_status(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Check if user has enough samples for analysis."""
    _verify_user_access(current_user, user_id)

    can_analyze, total_words = voice_service.can_analyze(user_id)
    samples = voice_service.get_samples(user_id)

    return {
        "sample_count": len(samples),
        "total_word_count": total_words,
        "min_words_required": 500,
        "can_analyze": can_analyze,
        "words_needed": max(0, 500 - total_words),
    }


# =============================================================================
# Analysis
# =============================================================================


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_voice(
    request: AnalyzeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Analyze voice from writing samples and save profile."""
    _verify_user_access(current_user, request.user_id)

    can_analyze, total_words = voice_service.can_analyze(request.user_id)
    if not can_analyze:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 500 words for analysis (have {total_words})",
        )

    try:
        result = voice_service.analyze_and_save(request.user_id)
        analysis = result["analysis"]
        return AnalysisResponse(
            profile_id=result["profile_id"],
            tone=analysis["tone"],
            sentence_patterns=analysis["sentence_patterns"],
            vocabulary_level=analysis["vocabulary_level"],
            signature_phrases=analysis["signature_phrases"],
            storytelling_style=analysis["storytelling_style"],
            emotional_register=analysis["emotional_register"],
            summary=analysis["summary"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Profile
# =============================================================================


@router.get("/users/{user_id}/profile", response_model=ProfileResponse)
def get_profile(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get user's default voice profile."""
    _verify_user_access(current_user, user_id)

    profile = voice_service.get_voice_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    return _profile_to_response(profile)


@router.get("/users/{user_id}/profiles", response_model=ProfilesResponse)
def get_profiles(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get all voice profiles for a user."""
    _verify_user_access(current_user, user_id)

    profiles = voice_service.get_all_profiles(user_id)
    return ProfilesResponse(
        profiles=[_profile_to_response(p) for p in profiles]
    )


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
def get_profile_by_id(
    profile_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get a specific voice profile by ID."""
    profile = voice_service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # Verify the profile belongs to the current user
    profile_user_id = profile.get("user_id")
    if profile_user_id:
        _verify_user_access(current_user, UUID(profile_user_id))

    return _profile_to_response(profile)


@router.put("/profiles/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: UUID,
    request: UpdateProfileRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Update voice profile metadata (name, description)."""
    profile = voice_service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # Verify the profile belongs to the current user
    profile_user_id = profile.get("user_id")
    if profile_user_id:
        _verify_user_access(current_user, UUID(profile_user_id))

    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.description is not None:
        updates["description"] = request.description

    if updates:
        voice_service.update_profile(profile_id, **updates)

    updated = voice_service.get_profile_by_id(profile_id)
    return _profile_to_response(updated)


@router.post("/profiles/{profile_id}/clone", response_model=ProfileResponse)
def clone_profile(
    profile_id: UUID,
    request: CloneProfileRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Clone a voice profile with a new name."""
    profile = voice_service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # Verify the profile belongs to the current user
    profile_user_id = profile.get("user_id")
    if profile_user_id:
        _verify_user_access(current_user, UUID(profile_user_id))

    try:
        new_id = voice_service.clone_profile(profile_id, request.new_name)
        profile = voice_service.get_profile_by_id(new_id)
        return _profile_to_response(profile)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/profiles/{profile_id}/set-default")
def set_default_profile(
    profile_id: UUID,
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Set a voice profile as the default."""
    _verify_user_access(current_user, user_id)

    profile = voice_service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    voice_service.set_default_profile(user_id, profile_id)
    return {"success": True, "profile_id": profile_id}


@router.delete("/profiles/{profile_id}")
def delete_profile(
    profile_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Delete a voice profile."""
    profile = voice_service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # Verify the profile belongs to the current user
    profile_user_id = profile.get("user_id")
    if profile_user_id:
        _verify_user_access(current_user, UUID(profile_user_id))

    voice_service.delete_profile(profile_id)
    return {"success": True, "deleted_id": profile_id}


def _profile_to_response(profile: dict) -> ProfileResponse:
    """Convert profile dict to response model."""
    return ProfileResponse(
        id=profile["id"],
        name=profile.get("name", "Default"),
        description=profile.get("description"),
        is_default=profile.get("is_default", False),
        tone=profile.get("tone"),
        sentence_patterns=profile.get("sentence_patterns", {}),
        vocabulary_level=profile.get("vocabulary_level"),
        signature_phrases=profile.get("signature_phrases", []),
        storytelling_style=profile.get("storytelling_style"),
        emotional_register=profile.get("emotional_register"),
        created_at=profile.get("created_at"),
    )
