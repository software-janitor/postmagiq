"""Workspace-scoped voice learning routes.

All voice learning operations (samples, analysis) are scoped to a workspace.
Voice prompts are shared and don't require workspace scoping.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceCtx,
    WorkspaceContext,
    require_workspace_scope,
)
from api.services.voice_service import VoiceService, WritingSample


router = APIRouter(prefix="/v1/w/{workspace_id}/voice", tags=["voice"])
voice_service = VoiceService()


# =============================================================================
# Request Models
# =============================================================================


class SaveSampleRequest(BaseModel):
    """Save a writing sample."""

    source_type: str  # "prompt" or "upload"
    content: str
    prompt_id: Optional[str] = None
    title: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Request voice analysis."""

    pass  # No additional fields needed - uses workspace context


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
    """Workspace's writing samples."""

    samples: list[dict]
    total_word_count: int
    can_analyze: bool


class SampleStatusResponse(BaseModel):
    """Sample status for analysis readiness."""

    sample_count: int
    total_word_count: int
    min_words_required: int
    can_analyze: bool
    words_needed: int


class AnalysisData(BaseModel):
    """Voice analysis data."""

    tone: str
    sentence_patterns: dict
    vocabulary_level: str
    signature_phrases: list[str]
    storytelling_style: str
    emotional_register: str
    summary: str


class AnalysisResponse(BaseModel):
    """Voice analysis result."""

    profile_id: str
    analysis: AnalysisData


# =============================================================================
# Prompts (shared, not workspace-scoped)
# =============================================================================


@router.get("/prompts", response_model=PromptsResponse)
async def get_prompts(
    ctx: WorkspaceCtx,
):
    """Get the 10 voice learning prompts.

    These prompts are shared across all workspaces.
    """
    return PromptsResponse(prompts=VoiceService.get_prompts())


@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: str,
    ctx: WorkspaceCtx,
):
    """Get a specific prompt by ID."""
    prompt = VoiceService.get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )
    return prompt


# =============================================================================
# Samples
# =============================================================================


@router.post("/samples", response_model=SampleResponse)
async def save_sample(
    request: SaveSampleRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))
    ],
):
    """Save a writing sample for the workspace.

    Requires strategy:write scope.
    """
    # Validate word count for prompt samples
    if request.source_type == "prompt":
        is_valid, word_count = VoiceService.validate_sample_word_count(
            request.content, max_words=500
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
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

    # Use workspace_id for scoping (via user_id from context)
    sample_id = voice_service.save_sample(
        ctx.user_id, sample, workspace_id=ctx.workspace_id
    )
    word_count = len(request.content.split())

    return SampleResponse(id=sample_id, word_count=word_count)


@router.get("/samples", response_model=SamplesResponse)
async def get_samples(
    ctx: WorkspaceCtx,
):
    """Get all writing samples for the workspace."""
    samples = voice_service.get_samples_for_workspace(ctx.workspace_id)
    total_words = voice_service.get_total_word_count_for_workspace(ctx.workspace_id)
    can_analyze = total_words >= 500

    return SamplesResponse(
        samples=samples,
        total_word_count=total_words,
        can_analyze=can_analyze,
    )


@router.get("/samples/status", response_model=SampleStatusResponse)
async def get_sample_status(
    ctx: WorkspaceCtx,
):
    """Check if workspace has enough samples for analysis."""
    samples = voice_service.get_samples_for_workspace(ctx.workspace_id)
    total_words = voice_service.get_total_word_count_for_workspace(ctx.workspace_id)
    can_analyze = total_words >= 500

    return SampleStatusResponse(
        sample_count=len(samples),
        total_word_count=total_words,
        min_words_required=500,
        can_analyze=can_analyze,
        words_needed=max(0, 500 - total_words),
    )


# =============================================================================
# Analysis
# =============================================================================


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_voice(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))
    ],
):
    """Analyze voice from writing samples and save profile.

    Requires strategy:write scope.
    Creates a new voice profile for the workspace.
    """
    total_words = voice_service.get_total_word_count_for_workspace(ctx.workspace_id)
    if total_words < 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Need at least 500 words for analysis (have {total_words})",
        )

    try:
        result = voice_service.analyze_and_save_for_workspace(
            ctx.workspace_id,
            ctx.user_id,
        )
        analysis = result["analysis"]
        return AnalysisResponse(
            profile_id=result["profile_id"],
            analysis=AnalysisData(
                tone=analysis["tone"],
                sentence_patterns=analysis["sentence_patterns"],
                vocabulary_level=analysis["vocabulary_level"],
                signature_phrases=analysis["signature_phrases"],
                storytelling_style=analysis["storytelling_style"],
                emotional_register=analysis["emotional_register"],
                summary=analysis.get("summary", ""),
            ),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice analysis failed: {str(e)}",
        )
