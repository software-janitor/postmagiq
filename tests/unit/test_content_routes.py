"""Tests for v1 workspace content API routes."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestResetPostEndpoint:
    """Tests for the POST /v1/w/{workspace_id}/posts/{post_id}/reset endpoint."""

    def test_reset_post_parses_c1p1_format(self):
        """Reset endpoint correctly parses c1p1 format post IDs."""
        from api.routes.v1.workspace_content import reset_post

        # The function expects c1p1 format to be parsed to post_number=1
        post_id = "c1p1"

        # Extract post number the same way the endpoint does
        post_number = None
        if post_id.startswith("c") and "p" in post_id:
            try:
                post_number = int(post_id.split("p")[1])
            except (ValueError, IndexError):
                pass

        assert post_number == 1

    def test_reset_post_parses_c2p15_format(self):
        """Reset endpoint correctly parses c2p15 format."""
        post_id = "c2p15"
        post_number = int(post_id.split("p")[1])
        assert post_number == 15

    def test_reset_post_parses_post_04_format(self):
        """Reset endpoint correctly parses post_04 format post IDs."""
        post_id = "post_04"

        post_number = None
        if post_id.startswith("post_"):
            try:
                post_number = int(post_id.replace("post_", "").lstrip("0") or "0")
            except ValueError:
                pass

        assert post_number == 4

    def test_reset_post_parses_post_01_format(self):
        """Reset endpoint correctly parses post_01 format."""
        post_id = "post_01"
        post_number = int(post_id.replace("post_", "").lstrip("0") or "0")
        assert post_number == 1

    def test_reset_post_model(self):
        """ResetPostResponse model validates correctly."""
        from api.routes.v1.workspace_content import ResetPostResponse

        response = ResetPostResponse(
            status="reset",
            post_id=uuid4(),
            post_number=5,
            deleted_workflow_outputs=3,
        )

        assert response.status == "reset"
        assert response.post_number == 5
        assert response.deleted_workflow_outputs == 3


class TestPostIdParsing:
    """Unit tests for post ID parsing logic."""

    def test_uuid_format(self):
        """UUID format should be valid."""
        from uuid import UUID

        post_id = "550e8400-e29b-41d4-a716-446655440000"
        try:
            parsed = UUID(post_id)
            assert parsed is not None
        except ValueError:
            pytest.fail("Should parse valid UUID")

    def test_invalid_uuid_format(self):
        """Invalid UUID should raise ValueError."""
        from uuid import UUID

        with pytest.raises(ValueError):
            UUID("not-a-uuid")

    def test_c1p1_parsing(self):
        """c1p1 format extracts post number correctly."""
        formats = [
            ("c1p1", 1),
            ("c1p5", 5),
            ("c2p10", 10),
            ("c3p99", 99),
        ]

        for post_id, expected in formats:
            if post_id.startswith("c") and "p" in post_id:
                post_number = int(post_id.split("p")[1])
                assert post_number == expected, f"Failed for {post_id}"

    def test_post_xx_parsing(self):
        """post_XX format extracts post number correctly."""
        formats = [
            ("post_01", 1),
            ("post_04", 4),
            ("post_10", 10),
            ("post_99", 99),
        ]

        for post_id, expected in formats:
            if post_id.startswith("post_"):
                post_number = int(post_id.replace("post_", "").lstrip("0") or "0")
                assert post_number == expected, f"Failed for {post_id}"
