"""API routes for post metadata.

Owner-only: Legacy tracker-based post metadata endpoints.
"""

from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, Depends

from api.auth.dependencies import CurrentUser, require_owner_role
from api.services.posts_service import (
    get_available_posts,
    get_all_posts,
    PostMetadata,
)

router = APIRouter(prefix="/posts", tags=["posts"])

# Path to content tracker
# In Docker: /app/linkedin_content_tracker.md (mounted)
# Local dev: ../linkedin_content_tracker.md (relative to orchestrator/)
TRACKER_PATH = Path("/app/linkedin_content_tracker.md")
if not TRACKER_PATH.exists():
    # Fallback for local development
    TRACKER_PATH = Path(__file__).parent.parent.parent.parent / "linkedin_content_tracker.md"


@router.get("/available", response_model=list[PostMetadata])
def list_available_posts(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Get posts that need stories (not started, needs story, draft)."""
    return get_available_posts(str(TRACKER_PATH))


@router.get("/all", response_model=list[PostMetadata])
def list_all_posts(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Get all posts from the tracker."""
    return get_all_posts(str(TRACKER_PATH))


@router.get("/next", response_model=PostMetadata | None)
def get_next_post(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Get the next unfinished post (lowest number that needs work)."""
    available = get_available_posts(str(TRACKER_PATH))
    if not available:
        return None
    # Return lowest post number
    return min(available, key=lambda p: p.post_number)


@router.get("/{post_id}", response_model=PostMetadata | None)
def get_post(
    post_id: str,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Get metadata for a specific post."""
    all_posts = get_all_posts(str(TRACKER_PATH))
    for post in all_posts:
        if post.post_id == post_id:
            return post
    return None
