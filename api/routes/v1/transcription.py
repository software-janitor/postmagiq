"""Workspace-scoped transcription routes.

Provides audio transcription from file uploads or YouTube URLs.
Uses Groq Whisper API for transcription.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, HttpUrl

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceContext,
    require_workspace_scope,
)
from api.services.transcription_service import (
    TranscriptionService,
    TranscriptionError,
    FileValidationError,
)
from api.services.youtube_service import (
    YouTubeServiceError,
    InvalidURLError,
    DurationExceededError,
    DownloadError,
)


router = APIRouter(prefix="/v1/w/{workspace_id}/transcribe", tags=["transcription"])
transcription_service = TranscriptionService()


# =============================================================================
# Request Models
# =============================================================================


class YouTubeTranscribeRequest(BaseModel):
    """Request to transcribe YouTube video audio."""

    url: str
    language: Optional[str] = None


# =============================================================================
# Response Models
# =============================================================================


class TranscriptionResponse(BaseModel):
    """Transcription result."""

    text: str
    language: Optional[str] = None
    duration_seconds: float
    tokens_used: int
    source_type: str  # "upload" or "youtube"
    source_info: dict


# =============================================================================
# Routes
# =============================================================================


@router.post("/upload", response_model=TranscriptionResponse)
async def transcribe_upload(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKFLOW_EXECUTE))
    ],
    audio: UploadFile = File(...),
    language: Optional[str] = None,
    prompt: Optional[str] = None,
):
    """Transcribe an uploaded audio file.

    Requires workflow:execute scope.

    Supported formats: mp3, wav, m4a, mp4, mpeg, mpga, webm, ogg
    Maximum file size: 25MB

    Args:
        audio: Audio file to transcribe
        language: Optional language code (e.g., "en")
        prompt: Optional prompt to guide transcription
    """
    # Validate file size
    if audio.size and audio.size > TranscriptionService.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {audio.size / 1024 / 1024:.1f}MB. "
            f"Maximum: {TranscriptionService.MAX_FILE_SIZE / 1024 / 1024:.0f}MB",
        )

    try:
        result = transcription_service.transcribe_file(
            audio_file=audio.file,
            filename=audio.filename or "audio.mp3",
            workspace_id=ctx.workspace_id,
            language=language,
            prompt=prompt,
        )

        return TranscriptionResponse(
            text=result.text,
            language=result.language,
            duration_seconds=result.duration_seconds,
            tokens_used=result.tokens_used,
            source_type=result.source_type,
            source_info=result.source_info,
        )

    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except TranscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/youtube", response_model=TranscriptionResponse)
async def transcribe_youtube(
    request: YouTubeTranscribeRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKFLOW_EXECUTE))
    ],
):
    """Transcribe audio from a YouTube video.

    Requires workflow:execute scope.

    Downloads audio from YouTube, transcribes it, then cleans up.
    Maximum video duration: 1 hour.

    Args:
        request: YouTube URL and optional language
    """
    try:
        result = transcription_service.transcribe_youtube(
            url=request.url,
            workspace_id=ctx.workspace_id,
            language=request.language,
        )

        return TranscriptionResponse(
            text=result.text,
            language=result.language,
            duration_seconds=result.duration_seconds,
            tokens_used=result.tokens_used,
            source_type=result.source_type,
            source_info=result.source_info,
        )

    except InvalidURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except DurationExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except DownloadError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download video: {e}",
        )
    except TranscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
