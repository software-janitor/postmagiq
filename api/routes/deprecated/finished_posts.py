"""API routes for viewing finished posts.

NOTE: publish/unpublish endpoints removed for security.
Use v1 workspace-scoped routes for future publish tracking.
"""

import json
import re
from pathlib import Path
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import CurrentUser, get_current_user
from api.services.content_service import ContentService
from runner.content.workflow_store import WorkflowStore

router = APIRouter(prefix="/finished-posts", tags=["finished-posts"])

content_service = ContentService()


def _workflow_store(user_id: UUID) -> WorkflowStore:
    """Create a workflow store bound to the specified user."""
    return WorkflowStore(user_id)


# Paths - adjust for Docker vs local
POSTS_DIR = Path("/app/posts")
IMAGES_DIR = Path("/app/images/prompts")
PUBLISH_STATUS_FILE = Path("/app/workflow/publish_status.json")

if not POSTS_DIR.exists():
    # Fallback for local development
    POSTS_DIR = Path(__file__).parent.parent.parent.parent / "posts"
    IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "images" / "prompts"
    PUBLISH_STATUS_FILE = (
        Path(__file__).parent.parent.parent / "workflow" / "publish_status.json"
    )

# Available platforms
PLATFORMS = ["linkedin", "threads", "medium", "x"]


class PublishInfo(BaseModel):
    """Publishing information for a post."""

    platform: str
    published_at: str
    url: Optional[str] = None


class PostPublishStatus(BaseModel):
    """Publish status for a post across platforms."""

    post_id: str
    platforms: list[PublishInfo] = []


class FinishedPost(BaseModel):
    """A finished post with content and image prompt."""

    post_id: str  # e.g., "c1p1"
    post_number: int
    chapter: int
    title: str
    content: str
    image_prompt: Optional[str] = None
    file_path: str
    publish_status: list[PublishInfo] = []


def _load_publish_status() -> dict:
    """Load publish status from JSON file."""
    if PUBLISH_STATUS_FILE.exists():
        return json.loads(PUBLISH_STATUS_FILE.read_text())
    return {}


def _save_publish_status(status: dict) -> None:
    """Save publish status to JSON file."""
    PUBLISH_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLISH_STATUS_FILE.write_text(json.dumps(status, indent=2))


def _get_post_publish_status(post_id: str) -> list[PublishInfo]:
    """Get publish status for a specific post."""
    status = _load_publish_status()
    post_status = status.get(post_id, {}).get("platforms", [])
    return [PublishInfo(**p) for p in post_status]


def _extract_title(content: str) -> str:
    """Extract title from first line of post content."""
    lines = content.strip().split("\n")
    if lines:
        return lines[0].strip()
    return "Untitled"


def _get_image_prompt_path(chapter: int, post_num: int) -> Optional[Path]:
    """Get image prompt file path if it exists."""
    # Try different naming conventions
    patterns = [
        f"c{chapter}p{post_num}_prompt.md",
        f"c{chapter}p{post_num:02d}_prompt.md",
    ]
    for pattern in patterns:
        path = IMAGES_DIR / pattern
        if path.exists():
            return path
    return None


@router.get("", response_model=list[FinishedPost])
def list_finished_posts(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """List all finished posts with their content and image prompts."""
    posts = []
    seen_posts = set()  # Track which posts we've added

    user_id = current_user.user_id
    store = _workflow_store(user_id)

    # Get ALL posts with status 'ready' or 'published' - these are finished posts
    # regardless of whether they have workflow outputs
    ready_posts = content_service.get_posts(user_id, status="ready")
    published_posts = content_service.get_posts(user_id, status="published")
    all_finished = ready_posts + published_posts

    for post in all_finished:
        chapter_num = post.chapter_number or 1
        post_id = f"c{chapter_num}p{post.post_number}"

        # Try to get content from workflow output first
        # Use get_latest_workflow_run_with_final to find runs that actually have final content
        story_id = f"post_{post.post_number:02d}"
        run = store.get_latest_workflow_run_with_final(user_id, story_id)

        final_content = None
        file_path = "no_workflow_run"

        if run:
            outputs = store.get_workflow_outputs(run.run_id)
            for output in outputs:
                if output.output_type == "final":
                    final_content = output.content
                    file_path = f"database:{run.run_id}"
                    break

        # If no workflow content, use topic as placeholder
        # (migrated posts may not have workflow runs)
        if not final_content:
            final_content = f"[Migrated post - content not available in workflow system]\n\nTopic: {post.topic or 'No topic'}"

        # Get image prompt if exists
        image_prompt = None
        image_path = _get_image_prompt_path(chapter_num, post.post_number)
        if image_path:
            image_prompt = image_path.read_text()

        # Use post topic as title, fall back to first line of content
        title = post.topic if post.topic else _extract_title(final_content)

        posts.append(
            FinishedPost(
                post_id=post_id,
                post_number=post.post_number,
                chapter=chapter_num,
                title=title,
                content=final_content,
                image_prompt=image_prompt,
                file_path=file_path,
                publish_status=_get_post_publish_status(post_id),
            )
        )
        seen_posts.add(post.post_number)

    # Also check file system for any posts not in database (legacy support)
    if POSTS_DIR.exists():
        for chapter_dir in sorted(POSTS_DIR.glob("chapter_*")):
            if not chapter_dir.is_dir():
                continue

            chapter_num = int(chapter_dir.name.replace("chapter_", ""))

            for post_file in sorted(chapter_dir.glob("post_*.md")):
                try:
                    post_num = int(post_file.stem.replace("post_", "").split("_")[0])
                except ValueError:
                    continue

                # Skip if already added from database
                if post_num in seen_posts:
                    continue

                content = post_file.read_text()

                # Try to get topic from database, fall back to first line of content
                post_record = content_service.get_post_by_number(user_id, post_num)
                title = (
                    post_record.topic
                    if post_record and post_record.topic
                    else _extract_title(content)
                )

                image_prompt = None
                image_path = _get_image_prompt_path(chapter_num, post_num)
                if image_path:
                    image_prompt = image_path.read_text()

                post_id = f"c{chapter_num}p{post_num}"
                posts.append(
                    FinishedPost(
                        post_id=post_id,
                        post_number=post_num,
                        chapter=chapter_num,
                        title=title,
                        content=content,
                        image_prompt=image_prompt,
                        file_path=str(post_file),
                        publish_status=_get_post_publish_status(post_id),
                    )
                )

    # Sort by post number
    posts.sort(key=lambda p: p.post_number)
    return posts


@router.get("/{post_id}", response_model=FinishedPost)
def get_finished_post(
    post_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get a specific finished post by ID (e.g., c1p1)."""
    # Parse post_id (format: c1p1, c1p02, etc.)
    match = re.match(r"c(\d+)p(\d+)", post_id)
    if not match:
        raise HTTPException(
            status_code=400, detail="Invalid post ID format. Use c1p1, c2p3, etc."
        )

    chapter_num = int(match.group(1))
    post_num = int(match.group(2))

    # First try database
    user_id = current_user.user_id
    store = _workflow_store(user_id)
    post_record = content_service.get_post_by_number(user_id, post_num)

    story_id = f"post_{post_num:02d}"
    run = store.get_latest_workflow_run_with_final(user_id, story_id)

    if run:
        outputs = store.get_workflow_outputs(run.run_id)
        final_content = None
        for output in outputs:
            if output.output_type == "final":
                final_content = output.content
                break

        if final_content:
            image_prompt = None
            image_path = _get_image_prompt_path(chapter_num, post_num)
            if image_path:
                image_prompt = image_path.read_text()

            # Use post topic as title, fall back to first line of content
            title = (
                post_record.topic
                if post_record and post_record.topic
                else _extract_title(final_content)
            )

            return FinishedPost(
                post_id=post_id,
                post_number=post_num,
                chapter=chapter_num,
                title=title,
                content=final_content,
                image_prompt=image_prompt,
                file_path=f"database:{run.run_id}",
                publish_status=_get_post_publish_status(post_id),
            )

    # Fallback to file system
    chapter_dir = POSTS_DIR / f"chapter_{chapter_num}"
    if not chapter_dir.exists():
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")

    post_file = None
    for pattern in [f"post_{post_num:02d}.md", f"post_{post_num}.md"]:
        candidate = chapter_dir / pattern
        if candidate.exists():
            post_file = candidate
            break

    if not post_file:
        raise HTTPException(
            status_code=404,
            detail=f"Post {post_num} not found in chapter {chapter_num}",
        )

    content = post_file.read_text()
    title = _extract_title(content)

    image_prompt = None
    image_path = _get_image_prompt_path(chapter_num, post_num)
    if image_path:
        image_prompt = image_path.read_text()

    return FinishedPost(
        post_id=post_id,
        post_number=post_num,
        chapter=chapter_num,
        title=title,
        content=content,
        image_prompt=image_prompt,
        file_path=str(post_file),
        publish_status=_get_post_publish_status(post_id),
    )


@router.get("/platforms")
def get_platforms():
    """Get list of available platforms."""
    return {"platforms": PLATFORMS}


# NOTE: publish/unpublish endpoints removed for security.
# Publish tracking will be reimplemented with proper auth in v1 routes.
# See: LAUNCH_SIMPLIFICATION_PLAN.md
