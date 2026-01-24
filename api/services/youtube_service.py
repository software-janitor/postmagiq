"""Service for downloading audio from YouTube videos using yt-dlp."""

import os
import re
import subprocess
import tempfile
from typing import Optional
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel


class YouTubeDownloadResult(BaseModel):
    """Result of a YouTube audio download."""

    audio_path: str
    title: str
    duration: float  # seconds
    video_id: str


class YouTubeServiceError(Exception):
    """Base exception for YouTube service errors."""

    pass


class InvalidURLError(YouTubeServiceError):
    """Raised when URL is not a valid YouTube URL."""

    pass


class DurationExceededError(YouTubeServiceError):
    """Raised when video duration exceeds the limit."""

    pass


class DownloadError(YouTubeServiceError):
    """Raised when download fails."""

    pass


class YouTubeService:
    """Service for downloading audio from YouTube videos.

    Uses yt-dlp to download audio in m4a format for transcription.
    Validates URLs against youtube.com/youtu.be domains.
    """

    ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
    MAX_DURATION_SECONDS = 3600  # 1 hour
    DOWNLOAD_TIMEOUT = 300  # 5 minutes

    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize YouTubeService.

        Args:
            temp_dir: Directory for temporary files. Uses system temp if not specified.
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()

    def _validate_url(self, url: str) -> str:
        """Validate and extract video ID from YouTube URL.

        Args:
            url: YouTube video URL

        Returns:
            Video ID

        Raises:
            InvalidURLError: If URL is not a valid YouTube URL
        """
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise InvalidURLError(f"Invalid URL format: {e}")

        # Check host
        host = parsed.netloc.lower()
        if host not in self.ALLOWED_HOSTS:
            raise InvalidURLError(
                f"URL must be from youtube.com or youtu.be, got: {host}"
            )

        # Extract video ID
        video_id = None
        if host == "youtu.be":
            # youtu.be/VIDEO_ID
            video_id = parsed.path.lstrip("/")
        else:
            # youtube.com/watch?v=VIDEO_ID
            query_params = parse_qs(parsed.query)
            video_ids = query_params.get("v", [])
            if video_ids:
                video_id = video_ids[0]

        if not video_id:
            raise InvalidURLError("Could not extract video ID from URL")

        # Basic video ID validation (11 chars, alphanumeric + - _)
        if not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
            raise InvalidURLError(f"Invalid video ID format: {video_id}")

        return video_id

    def _get_video_info(self, url: str) -> dict:
        """Get video metadata without downloading.

        Args:
            url: YouTube video URL

        Returns:
            dict with title, duration, video_id

        Raises:
            DownloadError: If metadata fetch fails
        """
        args = [
            "yt-dlp",
            "--no-download",
            "--print",
            "%(title)s\n%(duration)s\n%(id)s",
            url,
        ]

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise DownloadError(f"Failed to get video info: {result.stderr}")

            lines = result.stdout.strip().split("\n")
            if len(lines) < 3:
                raise DownloadError(f"Unexpected output format: {result.stdout}")

            title = lines[0]
            duration = float(lines[1]) if lines[1] else 0
            video_id = lines[2]

            return {
                "title": title,
                "duration": duration,
                "video_id": video_id,
            }

        except subprocess.TimeoutExpired:
            raise DownloadError("Timed out getting video info")
        except ValueError as e:
            raise DownloadError(f"Failed to parse video info: {e}")

    def download_audio(self, url: str) -> YouTubeDownloadResult:
        """Download audio from a YouTube video.

        Downloads in m4a format (best audio quality compatible with Whisper).
        Validates URL and checks duration before downloading.

        Args:
            url: YouTube video URL

        Returns:
            YouTubeDownloadResult with audio_path, title, duration, video_id

        Raises:
            InvalidURLError: If URL is not valid YouTube URL
            DurationExceededError: If video exceeds max duration
            DownloadError: If download fails
        """
        # Validate URL
        video_id = self._validate_url(url)

        # Get video info to check duration
        info = self._get_video_info(url)

        if info["duration"] > self.MAX_DURATION_SECONDS:
            raise DurationExceededError(
                f"Video duration ({info['duration']:.0f}s) exceeds maximum "
                f"({self.MAX_DURATION_SECONDS}s = 1 hour)"
            )

        # Prepare output path
        output_template = os.path.join(self.temp_dir, f"{video_id}.%(ext)s")
        output_path = os.path.join(self.temp_dir, f"{video_id}.m4a")

        try:
            # Download audio
            args = [
                "yt-dlp",
                "-x",  # Extract audio
                "--audio-format",
                "m4a",
                "-o",
                output_template,
                "--no-playlist",  # Don't download playlists
                "--no-part",  # Don't use .part files
                url,
            ]

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.DOWNLOAD_TIMEOUT,
            )

            if result.returncode != 0:
                raise DownloadError(f"Download failed: {result.stderr}")

            # Verify file exists
            if not os.path.exists(output_path):
                # Sometimes yt-dlp outputs with different extension
                possible_paths = [
                    os.path.join(self.temp_dir, f"{video_id}.{ext}")
                    for ext in ["m4a", "mp3", "opus", "webm"]
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        output_path = path
                        break
                else:
                    raise DownloadError(
                        f"Downloaded file not found at expected path: {output_path}"
                    )

            return YouTubeDownloadResult(
                audio_path=output_path,
                title=info["title"],
                duration=info["duration"],
                video_id=video_id,
            )

        except subprocess.TimeoutExpired:
            # Cleanup partial download
            if os.path.exists(output_path):
                os.remove(output_path)
            raise DownloadError(
                f"Download timed out after {self.DOWNLOAD_TIMEOUT} seconds"
            )

    def cleanup(self, audio_path: str) -> None:
        """Remove downloaded audio file.

        Args:
            audio_path: Path to audio file to delete
        """
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except OSError:
            pass  # Ignore cleanup errors
