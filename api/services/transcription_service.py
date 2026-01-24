"""Service for audio transcription using Groq Whisper API."""

import os
from typing import BinaryIO, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from api.services.youtube_service import (
    YouTubeService,
    YouTubeServiceError,
)
from runner.agents.groq_api import GroqAPIAgent


class TranscriptionResult(BaseModel):
    """Result of audio transcription."""

    text: str
    language: Optional[str] = None
    duration_seconds: float
    tokens_used: int
    source_type: Literal["upload", "youtube"]
    source_info: dict


class TranscriptionError(Exception):
    """Base exception for transcription errors."""

    pass


class FileValidationError(TranscriptionError):
    """Raised when file validation fails."""

    pass


class TranscriptionService:
    """Service for transcribing audio files using Groq Whisper API.

    Supports:
    - Direct file uploads (mp3, wav, m4a, mp4)
    - YouTube URL transcription (downloads then transcribes)
    """

    ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "mpeg", "mpga", "webm", "ogg"}
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

    def __init__(
        self,
        youtube_service: Optional[YouTubeService] = None,
        groq_agent: Optional[GroqAPIAgent] = None,
    ):
        """Initialize TranscriptionService.

        Args:
            youtube_service: YouTubeService instance for YouTube downloads
            groq_agent: GroqAPIAgent instance for transcription
        """
        self.youtube_service = youtube_service or YouTubeService()
        self._groq_agent = groq_agent

    @property
    def groq_agent(self) -> GroqAPIAgent:
        """Lazy-load GroqAPIAgent to avoid initialization errors when GROQ_API_KEY not set."""
        if self._groq_agent is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise TranscriptionError("GROQ_API_KEY environment variable not set")
            self._groq_agent = GroqAPIAgent({"model": "whisper", "api_key": api_key})
        return self._groq_agent

    def _validate_file(self, filename: str, file_size: Optional[int] = None) -> None:
        """Validate uploaded file.

        Args:
            filename: Name of the file
            file_size: Size in bytes (optional)

        Raises:
            FileValidationError: If validation fails
        """
        # Check extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in self.ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"Invalid file type: .{ext}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )

        # Check size
        if file_size is not None and file_size > self.MAX_FILE_SIZE:
            raise FileValidationError(
                f"File too large: {file_size / 1024 / 1024:.1f}MB. "
                f"Maximum: {self.MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )

    def transcribe_file(
        self,
        audio_file: BinaryIO,
        filename: str,
        workspace_id: UUID,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe an uploaded audio file.

        Args:
            audio_file: File-like object opened in binary mode
            filename: Original filename (used for extension validation)
            workspace_id: Workspace ID for usage tracking
            language: Optional language code (e.g., "en")
            prompt: Optional prompt to guide transcription

        Returns:
            TranscriptionResult with transcription text and metadata

        Raises:
            FileValidationError: If file validation fails
            TranscriptionError: If transcription fails
        """
        self._validate_file(filename)

        try:
            result = self.groq_agent.transcribe(
                audio_file=audio_file,
                model="whisper-large-v3",
                language=language,
                prompt=prompt,
            )

            return TranscriptionResult(
                text=result["text"],
                language=result.get("language"),
                duration_seconds=result.get("duration", 0),
                tokens_used=result.get("tokens", 1),
                source_type="upload",
                source_info={"filename": filename},
            )

        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def transcribe_youtube(
        self,
        url: str,
        workspace_id: UUID,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio from a YouTube video.

        Downloads the audio, transcribes it, then cleans up the temp file.

        Args:
            url: YouTube video URL
            workspace_id: Workspace ID for usage tracking
            language: Optional language code (e.g., "en")
            prompt: Optional prompt to guide transcription

        Returns:
            TranscriptionResult with transcription text and metadata

        Raises:
            YouTubeServiceError: If download fails (InvalidURLError, DurationExceededError, DownloadError)
            TranscriptionError: If transcription fails
        """
        download_result = None
        try:
            # Download audio
            download_result = self.youtube_service.download_audio(url)

            # Transcribe
            with open(download_result.audio_path, "rb") as audio_file:
                result = self.groq_agent.transcribe(
                    audio_file=audio_file,
                    model="whisper-large-v3",
                    language=language,
                    prompt=prompt,
                )

            return TranscriptionResult(
                text=result["text"],
                language=result.get("language"),
                duration_seconds=download_result.duration,
                tokens_used=result.get("tokens", 1),
                source_type="youtube",
                source_info={
                    "video_id": download_result.video_id,
                    "title": download_result.title,
                    "url": url,
                },
            )

        except YouTubeServiceError:
            # Re-raise YouTube errors as-is
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")
        finally:
            # Cleanup downloaded file
            if download_result:
                self.youtube_service.cleanup(download_result.audio_path)
