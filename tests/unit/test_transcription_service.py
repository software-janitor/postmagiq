"""Unit tests for TranscriptionService.

Tests file validation, transcription handling, and YouTube integration
using mocked GroqAPIAgent and YouTubeService.
"""

import io
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from api.services.transcription_service import (
    TranscriptionService,
    TranscriptionResult,
    TranscriptionError,
    FileValidationError,
)
from api.services.youtube_service import (
    YouTubeService,
    YouTubeDownloadResult,
    InvalidURLError,
    DurationExceededError,
    DownloadError,
)


@pytest.fixture
def mock_groq_agent():
    """Create a mock GroqAPIAgent."""
    agent = Mock()
    agent.transcribe.return_value = {
        "text": "Hello, this is a test transcription.",
        "language": "en",
        "duration": 30.5,
        "tokens": 2,
    }
    return agent


@pytest.fixture
def mock_youtube_service():
    """Create a mock YouTubeService."""
    service = Mock(spec=YouTubeService)
    return service


@pytest.fixture
def transcription_service(mock_groq_agent, mock_youtube_service):
    """Create TranscriptionService with mocked dependencies."""
    return TranscriptionService(
        youtube_service=mock_youtube_service,
        groq_agent=mock_groq_agent,
    )


class TestFileValidation:
    """Tests for file validation."""

    def test_valid_mp3_file(self, transcription_service):
        """Test validation passes for MP3 files."""
        # Should not raise
        transcription_service._validate_file("audio.mp3")

    def test_valid_wav_file(self, transcription_service):
        """Test validation passes for WAV files."""
        transcription_service._validate_file("audio.wav")

    def test_valid_m4a_file(self, transcription_service):
        """Test validation passes for M4A files."""
        transcription_service._validate_file("audio.m4a")

    def test_valid_mp4_file(self, transcription_service):
        """Test validation passes for MP4 files."""
        transcription_service._validate_file("video.mp4")

    def test_invalid_extension(self, transcription_service):
        """Test rejection of unsupported file types."""
        with pytest.raises(FileValidationError) as exc:
            transcription_service._validate_file("document.pdf")
        assert "Invalid file type" in str(exc.value)

    def test_file_too_large(self, transcription_service):
        """Test rejection of files exceeding size limit."""
        with pytest.raises(FileValidationError) as exc:
            # 30 MB
            transcription_service._validate_file("audio.mp3", file_size=30 * 1024 * 1024)
        assert "too large" in str(exc.value)

    def test_file_at_size_limit(self, transcription_service):
        """Test acceptance of files at exactly the size limit."""
        # Should not raise - exactly 25 MB
        transcription_service._validate_file(
            "audio.mp3", file_size=25 * 1024 * 1024
        )

    def test_missing_extension(self, transcription_service):
        """Test rejection of files without extension."""
        with pytest.raises(FileValidationError):
            transcription_service._validate_file("audiofile")


class TestTranscribeFile:
    """Tests for file transcription."""

    def test_transcribe_file_success(self, transcription_service, mock_groq_agent):
        """Test successful file transcription."""
        workspace_id = uuid4()
        audio_file = io.BytesIO(b"fake audio data")

        result = transcription_service.transcribe_file(
            audio_file=audio_file,
            filename="test.mp3",
            workspace_id=workspace_id,
        )

        assert result.text == "Hello, this is a test transcription."
        assert result.language == "en"
        assert result.duration_seconds == 30.5
        assert result.tokens_used == 2
        assert result.source_type == "upload"
        assert result.source_info["filename"] == "test.mp3"

        mock_groq_agent.transcribe.assert_called_once()

    def test_transcribe_file_with_language(self, transcription_service, mock_groq_agent):
        """Test file transcription with language hint."""
        workspace_id = uuid4()
        audio_file = io.BytesIO(b"fake audio data")

        transcription_service.transcribe_file(
            audio_file=audio_file,
            filename="test.mp3",
            workspace_id=workspace_id,
            language="es",
        )

        call_kwargs = mock_groq_agent.transcribe.call_args[1]
        assert call_kwargs["language"] == "es"

    def test_transcribe_file_with_prompt(self, transcription_service, mock_groq_agent):
        """Test file transcription with prompt."""
        workspace_id = uuid4()
        audio_file = io.BytesIO(b"fake audio data")

        transcription_service.transcribe_file(
            audio_file=audio_file,
            filename="test.mp3",
            workspace_id=workspace_id,
            prompt="Technical podcast about software",
        )

        call_kwargs = mock_groq_agent.transcribe.call_args[1]
        assert call_kwargs["prompt"] == "Technical podcast about software"

    def test_transcribe_file_invalid_type(self, transcription_service):
        """Test rejection of invalid file type."""
        workspace_id = uuid4()
        audio_file = io.BytesIO(b"fake data")

        with pytest.raises(FileValidationError):
            transcription_service.transcribe_file(
                audio_file=audio_file,
                filename="document.pdf",
                workspace_id=workspace_id,
            )

    def test_transcribe_file_api_error(self, transcription_service, mock_groq_agent):
        """Test handling of API errors during transcription."""
        workspace_id = uuid4()
        audio_file = io.BytesIO(b"fake audio data")
        mock_groq_agent.transcribe.side_effect = Exception("API rate limit exceeded")

        with pytest.raises(TranscriptionError) as exc:
            transcription_service.transcribe_file(
                audio_file=audio_file,
                filename="test.mp3",
                workspace_id=workspace_id,
            )
        assert "Transcription failed" in str(exc.value)


class TestTranscribeYouTube:
    """Tests for YouTube transcription."""

    def test_transcribe_youtube_success(
        self, transcription_service, mock_youtube_service, mock_groq_agent, tmp_path
    ):
        """Test successful YouTube transcription."""
        workspace_id = uuid4()

        # Create fake audio file
        audio_file = tmp_path / "video123.m4a"
        audio_file.write_bytes(b"fake audio content")

        # Mock YouTube download
        mock_youtube_service.download_audio.return_value = YouTubeDownloadResult(
            audio_path=str(audio_file),
            title="Test Video Title",
            duration=180.0,
            video_id="video123",
        )

        result = transcription_service.transcribe_youtube(
            url="https://youtu.be/video123abc",
            workspace_id=workspace_id,
        )

        assert result.text == "Hello, this is a test transcription."
        assert result.source_type == "youtube"
        assert result.source_info["video_id"] == "video123"
        assert result.source_info["title"] == "Test Video Title"
        assert result.duration_seconds == 180.0

        # Verify cleanup was called
        mock_youtube_service.cleanup.assert_called_once_with(str(audio_file))

    def test_transcribe_youtube_invalid_url(
        self, transcription_service, mock_youtube_service
    ):
        """Test handling of invalid YouTube URL."""
        workspace_id = uuid4()
        mock_youtube_service.download_audio.side_effect = InvalidURLError(
            "URL must be from youtube.com"
        )

        with pytest.raises(InvalidURLError):
            transcription_service.transcribe_youtube(
                url="https://vimeo.com/123",
                workspace_id=workspace_id,
            )

    def test_transcribe_youtube_duration_exceeded(
        self, transcription_service, mock_youtube_service
    ):
        """Test handling of video duration limit."""
        workspace_id = uuid4()
        mock_youtube_service.download_audio.side_effect = DurationExceededError(
            "Video exceeds 1 hour limit"
        )

        with pytest.raises(DurationExceededError):
            transcription_service.transcribe_youtube(
                url="https://youtu.be/longvideo1",
                workspace_id=workspace_id,
            )

    def test_transcribe_youtube_download_error(
        self, transcription_service, mock_youtube_service
    ):
        """Test handling of download failure."""
        workspace_id = uuid4()
        mock_youtube_service.download_audio.side_effect = DownloadError(
            "Network timeout"
        )

        with pytest.raises(DownloadError):
            transcription_service.transcribe_youtube(
                url="https://youtu.be/video123abc",
                workspace_id=workspace_id,
            )

    def test_transcribe_youtube_api_error_cleanup(
        self, transcription_service, mock_youtube_service, mock_groq_agent, tmp_path
    ):
        """Test cleanup happens even when transcription fails."""
        workspace_id = uuid4()

        # Create fake audio file
        audio_file = tmp_path / "video123.m4a"
        audio_file.write_bytes(b"fake audio content")

        mock_youtube_service.download_audio.return_value = YouTubeDownloadResult(
            audio_path=str(audio_file),
            title="Test Video",
            duration=60.0,
            video_id="video123",
        )
        mock_groq_agent.transcribe.side_effect = Exception("API error")

        with pytest.raises(TranscriptionError):
            transcription_service.transcribe_youtube(
                url="https://youtu.be/video123abc",
                workspace_id=workspace_id,
            )

        # Verify cleanup was still called
        mock_youtube_service.cleanup.assert_called_once_with(str(audio_file))


class TestGroqAgentLazyLoad:
    """Tests for lazy loading of GroqAPIAgent."""

    def test_groq_agent_lazy_load_no_api_key(self):
        """Test error when GROQ_API_KEY not set."""
        service = TranscriptionService(
            youtube_service=Mock(),
            groq_agent=None,  # Force lazy load
        )

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(TranscriptionError) as exc:
                _ = service.groq_agent
            assert "GROQ_API_KEY" in str(exc.value)

    def test_groq_agent_lazy_load_with_api_key(self):
        """Test successful lazy load with API key."""
        service = TranscriptionService(
            youtube_service=Mock(),
            groq_agent=None,
        )

        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
            with patch("api.services.transcription_service.GroqAPIAgent") as MockAgent:
                MockAgent.return_value = Mock()
                agent = service.groq_agent

                MockAgent.assert_called_once()
                assert agent is not None
