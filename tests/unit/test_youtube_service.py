"""Unit tests for YouTubeService.

Tests URL validation, video info extraction, and download handling
using mocked subprocess calls.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from api.services.youtube_service import (
    YouTubeService,
    YouTubeDownloadResult,
    InvalidURLError,
    DurationExceededError,
    DownloadError,
)


class TestURLValidation:
    """Tests for YouTube URL validation."""

    def test_valid_youtube_watch_url(self):
        """Test validation of standard YouTube watch URL."""
        service = YouTubeService()
        video_id = service._validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_valid_youtu_be_url(self):
        """Test validation of short youtu.be URL."""
        service = YouTubeService()
        video_id = service._validate_url("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_valid_mobile_url(self):
        """Test validation of mobile YouTube URL."""
        service = YouTubeService()
        video_id = service._validate_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_invalid_host(self):
        """Test rejection of non-YouTube hosts."""
        service = YouTubeService()
        with pytest.raises(InvalidURLError) as exc:
            service._validate_url("https://vimeo.com/123456")
        assert "youtube.com or youtu.be" in str(exc.value)

    def test_missing_video_id(self):
        """Test rejection of URL without video ID."""
        service = YouTubeService()
        with pytest.raises(InvalidURLError) as exc:
            service._validate_url("https://www.youtube.com/")
        assert "Could not extract video ID" in str(exc.value)

    def test_invalid_video_id_format(self):
        """Test rejection of malformed video ID."""
        service = YouTubeService()
        with pytest.raises(InvalidURLError) as exc:
            service._validate_url("https://youtu.be/short")
        assert "Invalid video ID format" in str(exc.value)

    def test_invalid_url_format(self):
        """Test rejection of completely invalid URL."""
        service = YouTubeService()
        with pytest.raises(InvalidURLError):
            service._validate_url("not a url at all")


class TestGetVideoInfo:
    """Tests for video metadata extraction."""

    def test_get_video_info_success(self):
        """Test successful video info retrieval."""
        service = YouTubeService()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Test Video Title\n300.5\ndQw4w9WgXcQ\n"

        with patch("subprocess.run", return_value=mock_result):
            info = service._get_video_info("https://youtu.be/dQw4w9WgXcQ")

        assert info["title"] == "Test Video Title"
        assert info["duration"] == 300.5
        assert info["video_id"] == "dQw4w9WgXcQ"

    def test_get_video_info_failure(self):
        """Test handling of yt-dlp failure."""
        service = YouTubeService()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Video unavailable"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(DownloadError) as exc:
                service._get_video_info("https://youtu.be/invalid123")
            assert "Failed to get video info" in str(exc.value)

    def test_get_video_info_timeout(self):
        """Test handling of timeout during info fetch."""
        service = YouTubeService()

        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("yt-dlp", 30)):
            with pytest.raises(DownloadError) as exc:
                service._get_video_info("https://youtu.be/dQw4w9WgXcQ")
            assert "Timed out" in str(exc.value)


class TestDownloadAudio:
    """Tests for audio download functionality."""

    def test_download_audio_success(self, tmp_path):
        """Test successful audio download."""
        service = YouTubeService(temp_dir=str(tmp_path))

        # Create a fake audio file
        audio_file = tmp_path / "dQw4w9WgXcQ.m4a"
        audio_file.write_bytes(b"fake audio content")

        # Mock video info
        info_result = MagicMock()
        info_result.returncode = 0
        info_result.stdout = "Test Video\n120.0\ndQw4w9WgXcQ\n"

        # Mock download
        download_result = MagicMock()
        download_result.returncode = 0
        download_result.stdout = ""

        with patch("subprocess.run", side_effect=[info_result, download_result]):
            result = service.download_audio("https://youtu.be/dQw4w9WgXcQ")

        assert result.video_id == "dQw4w9WgXcQ"
        assert result.title == "Test Video"
        assert result.duration == 120.0
        assert result.audio_path == str(audio_file)

    def test_download_audio_duration_exceeded(self):
        """Test rejection of videos exceeding max duration."""
        service = YouTubeService()

        # Mock video info with duration > 1 hour
        info_result = MagicMock()
        info_result.returncode = 0
        info_result.stdout = "Long Video\n7200.0\ndQw4w9WgXcQ\n"  # 2 hours

        with patch("subprocess.run", return_value=info_result):
            with pytest.raises(DurationExceededError) as exc:
                service.download_audio("https://youtu.be/dQw4w9WgXcQ")
            assert "exceeds maximum" in str(exc.value)

    def test_download_audio_invalid_url(self):
        """Test rejection of invalid YouTube URL."""
        service = YouTubeService()
        with pytest.raises(InvalidURLError):
            service.download_audio("https://example.com/video")

    def test_download_audio_download_failure(self, tmp_path):
        """Test handling of download failure."""
        service = YouTubeService(temp_dir=str(tmp_path))

        # Mock video info
        info_result = MagicMock()
        info_result.returncode = 0
        info_result.stdout = "Test Video\n120.0\ndQw4w9WgXcQ\n"

        # Mock failed download
        download_result = MagicMock()
        download_result.returncode = 1
        download_result.stderr = "Network error"

        with patch("subprocess.run", side_effect=[info_result, download_result]):
            with pytest.raises(DownloadError) as exc:
                service.download_audio("https://youtu.be/dQw4w9WgXcQ")
            assert "Download failed" in str(exc.value)

    def test_download_audio_file_not_found(self, tmp_path):
        """Test handling when downloaded file is not found."""
        service = YouTubeService(temp_dir=str(tmp_path))

        # Mock video info
        info_result = MagicMock()
        info_result.returncode = 0
        info_result.stdout = "Test Video\n120.0\ndQw4w9WgXcQ\n"

        # Mock successful download but file doesn't exist
        download_result = MagicMock()
        download_result.returncode = 0
        download_result.stdout = ""

        with patch("subprocess.run", side_effect=[info_result, download_result]):
            with pytest.raises(DownloadError) as exc:
                service.download_audio("https://youtu.be/dQw4w9WgXcQ")
            assert "not found" in str(exc.value)


class TestCleanup:
    """Tests for file cleanup functionality."""

    def test_cleanup_existing_file(self, tmp_path):
        """Test cleanup removes existing file."""
        service = YouTubeService()
        test_file = tmp_path / "test.m4a"
        test_file.write_bytes(b"test")

        service.cleanup(str(test_file))
        assert not test_file.exists()

    def test_cleanup_nonexistent_file(self, tmp_path):
        """Test cleanup handles nonexistent file gracefully."""
        service = YouTubeService()
        # Should not raise
        service.cleanup(str(tmp_path / "nonexistent.m4a"))
