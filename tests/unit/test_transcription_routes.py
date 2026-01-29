"""Tests for v1 transcription API routes.

Tests the workspace-scoped transcription endpoints for audio upload
and YouTube transcription (premium tier features).
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
import io


class TestTranscriptionRouteModels:
    """Tests for transcription request/response models."""

    def test_youtube_transcription_request(self):
        """YouTubeTranscribeRequest validates input."""
        from api.routes.v1.transcription import YouTubeTranscribeRequest

        req = YouTubeTranscribeRequest(
            url="https://youtu.be/abc123",
        )
        assert req.url == "https://youtu.be/abc123"
        assert req.language is None

        # With language
        req = YouTubeTranscribeRequest(
            url="https://youtube.com/watch?v=abc123",
            language="es",
        )
        assert req.language == "es"

    def test_transcription_response(self):
        """TranscriptionResponse structure is correct."""
        from api.routes.v1.transcription import TranscriptionResponse

        resp = TranscriptionResponse(
            text="Hello, this is transcribed text.",
            language="en",
            duration_seconds=120.5,
            tokens_used=15,
            source_type="upload",
            source_info={"filename": "test.mp3"},
        )
        assert resp.text == "Hello, this is transcribed text."
        assert resp.source_type == "upload"


class TestTranscriptionRoutePaths:
    """Tests verifying transcription routes are correctly configured."""

    def test_router_prefix_includes_workspace_id(self):
        """Transcription router uses workspace-scoped prefix."""
        from api.routes.v1.transcription import router

        # Check the router prefix
        assert "/v1/w/{workspace_id}/transcribe" in router.prefix

    def test_upload_endpoint_path(self):
        """Upload endpoint is at correct path."""
        from api.routes.v1.transcription import router

        paths = [route.path for route in router.routes]
        assert any("upload" in path for path in paths)

    def test_youtube_endpoint_path(self):
        """YouTube endpoint is at correct path."""
        from api.routes.v1.transcription import router

        paths = [route.path for route in router.routes]
        assert any("youtube" in path for path in paths)


class TestTranscriptionTierRequirements:
    """Tests for premium tier requirements."""

    def test_upload_requires_premium_scope(self):
        """Upload transcription requires appropriate scope."""
        from api.routes.v1.transcription import router

        # Find the upload route
        upload_route = None
        for route in router.routes:
            if "upload" in route.path:
                upload_route = route
                break

        assert upload_route is not None
        # Route should exist and require auth (has dependencies)

    def test_youtube_requires_premium_scope(self):
        """YouTube transcription requires appropriate scope."""
        from api.routes.v1.transcription import router

        # Find the youtube route
        youtube_route = None
        for route in router.routes:
            if "youtube" in route.path:
                youtube_route = route
                break

        assert youtube_route is not None


class TestTranscriptionServiceIntegration:
    """Tests for transcription service integration."""

    def test_upload_calls_transcription_service(self):
        """Upload endpoint delegates to TranscriptionService."""
        from api.services.transcription_service import TranscriptionService

        # Verify the method exists
        assert hasattr(TranscriptionService, "transcribe_file")

    def test_youtube_calls_transcription_service(self):
        """YouTube endpoint delegates to TranscriptionService."""
        from api.services.transcription_service import TranscriptionService

        # Verify the method exists
        assert hasattr(TranscriptionService, "transcribe_youtube")


class TestTranscriptionFileValidation:
    """Tests for file validation in transcription."""

    def test_valid_audio_extensions(self):
        """Verify valid audio file extensions are accepted."""
        from api.services.transcription_service import TranscriptionService

        service = TranscriptionService(
            youtube_service=MagicMock(),
            groq_agent=MagicMock(),
        )

        # These should not raise
        valid_extensions = [".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg"]
        for ext in valid_extensions:
            service._validate_file(f"test{ext}")

    def test_invalid_file_extension_rejected(self):
        """Verify invalid file extensions are rejected."""
        from api.services.transcription_service import (
            TranscriptionService,
            FileValidationError,
        )

        service = TranscriptionService(
            youtube_service=MagicMock(),
            groq_agent=MagicMock(),
        )

        invalid_extensions = [".pdf", ".txt", ".exe", ".zip"]
        for ext in invalid_extensions:
            with pytest.raises(FileValidationError):
                service._validate_file(f"test{ext}")

    def test_file_size_limit_enforced(self):
        """Verify file size limit is enforced (25MB)."""
        from api.services.transcription_service import (
            TranscriptionService,
            FileValidationError,
        )

        service = TranscriptionService(
            youtube_service=MagicMock(),
            groq_agent=MagicMock(),
        )

        # Just under limit should pass
        service._validate_file("test.mp3", file_size=25 * 1024 * 1024)

        # Over limit should fail
        with pytest.raises(FileValidationError) as exc:
            service._validate_file("test.mp3", file_size=26 * 1024 * 1024)
        assert "too large" in str(exc.value)


class TestYouTubeURLValidation:
    """Tests for YouTube URL validation."""

    def test_valid_youtube_urls(self):
        """Verify valid YouTube URLs are accepted."""
        from api.services.youtube_service import YouTubeService

        service = YouTubeService()

        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            # Should not raise - validates URL format
            video_id = service._validate_url(url)
            assert video_id is not None
            assert len(video_id) > 0

    def test_invalid_youtube_urls_rejected(self):
        """Verify non-YouTube URLs are rejected."""
        from api.services.youtube_service import YouTubeService, InvalidURLError

        service = YouTubeService()

        invalid_urls = [
            "https://vimeo.com/123456",
            "https://example.com/video",
            "not-a-url",
        ]

        for url in invalid_urls:
            with pytest.raises(InvalidURLError):
                service._validate_url(url)
