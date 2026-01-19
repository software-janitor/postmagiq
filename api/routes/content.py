"""API routes for content strategy database."""

import os
import re
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Annotated

from api.auth.dependencies import CurrentUser, get_current_user
from api.services.content_service import ContentService
from api.services.image_prompt_service import ImagePromptService
from runner.content.models import (
    UserResponse,
    GoalResponse,
    ChapterResponse,
    PostResponse,
    VoiceProfileResponse,
    WritingSampleRecord,
)

router = APIRouter(prefix="/content", tags=["content"])
content_service = ContentService()


# =============================================================================
# Request Models
# =============================================================================


class CreateUserRequest(BaseModel):
    name: str
    email: Optional[str] = None


class SaveGoalRequest(BaseModel):
    user_id: UUID
    strategy_type: str = "series"
    positioning: Optional[str] = None
    signature_thesis: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None
    onboarding_mode: Optional[str] = None
    onboarding_transcript: Optional[str] = None


class UpdateGoalRequest(BaseModel):
    strategy_type: Optional[str] = None
    voice_profile_id: Optional[UUID] = None
    image_config_set_id: Optional[UUID] = None
    positioning: Optional[str] = None
    signature_thesis: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None


class SaveChapterRequest(BaseModel):
    user_id: UUID
    chapter_number: int
    title: str
    description: Optional[str] = None
    theme: Optional[str] = None
    theme_description: Optional[str] = None
    weeks_start: Optional[int] = None
    weeks_end: Optional[int] = None


class SavePostRequest(BaseModel):
    user_id: UUID
    chapter_id: UUID
    post_number: int
    topic: Optional[str] = None
    shape: Optional[str] = None
    cadence: Optional[str] = None
    entry_point: Optional[str] = None
    status: str = "not_started"
    guidance: Optional[str] = None


class UpdatePostRequest(BaseModel):
    topic: Optional[str] = None
    shape: Optional[str] = None
    cadence: Optional[str] = None
    entry_point: Optional[str] = None
    status: Optional[str] = None
    story_used: Optional[str] = None
    published_url: Optional[str] = None
    guidance: Optional[str] = None


class SaveWritingSampleRequest(BaseModel):
    user_id: UUID
    source_type: str  # "prompt" or "upload"
    content: str
    prompt_id: Optional[str] = None
    prompt_text: Optional[str] = None
    title: Optional[str] = None


class SaveVoiceProfileRequest(BaseModel):
    user_id: UUID
    tone: Optional[str] = None
    sentence_patterns: Optional[str] = None
    vocabulary_level: Optional[str] = None
    signature_phrases: Optional[str] = None
    storytelling_style: Optional[str] = None
    emotional_register: Optional[str] = None
    raw_analysis: Optional[str] = None


class UpdateVoiceProfileRequest(BaseModel):
    tone: Optional[str] = None
    sentence_patterns: Optional[str] = None
    vocabulary_level: Optional[str] = None
    signature_phrases: Optional[str] = None
    storytelling_style: Optional[str] = None
    emotional_register: Optional[str] = None
    raw_analysis: Optional[str] = None


# =============================================================================
# User Endpoints
# =============================================================================


@router.get("/users", response_model=list[UserResponse])
def list_users():
    """List all users with summary data."""
    return content_service.list_users()


@router.post("/users", response_model=dict)
def create_user(request: CreateUserRequest):
    """Create a new user."""
    user_id = content_service.create_user(request.name, request.email)
    return {"id": user_id}


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID):
    """Get user with summary data."""
    user = content_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/email/{email}", response_model=UserResponse)
def get_user_by_email(email: str):
    """Get user by email."""
    user = content_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# =============================================================================
# Goal Endpoints
# =============================================================================


@router.post("/goals", response_model=dict)
def save_goal(request: SaveGoalRequest):
    """Save a new goal for a user."""
    goal_id = content_service.save_goal(
        user_id=request.user_id,
        strategy_type=request.strategy_type,
        positioning=request.positioning,
        signature_thesis=request.signature_thesis,
        target_audience=request.target_audience,
        content_style=request.content_style,
        onboarding_mode=request.onboarding_mode,
        onboarding_transcript=request.onboarding_transcript,
    )
    return {"id": goal_id}


@router.get("/users/{user_id}/goal", response_model=GoalResponse)
def get_goal(user_id: UUID):
    """Get user's goal."""
    goal = content_service.get_goal(user_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.put("/goals/{goal_id}")
def update_goal(goal_id: UUID, request: UpdateGoalRequest):
    """Update goal fields."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    content_service.update_goal(goal_id, **updates)
    return {"status": "updated"}


@router.delete("/goals/{goal_id}")
def delete_strategy(goal_id: UUID, user_id: Optional[UUID] = None):
    """Delete a strategy (goal) and all related chapters and posts."""
    result = content_service.delete_strategy(user_id, goal_id)
    return result


# =============================================================================
# Chapter Endpoints
# =============================================================================


@router.post("/chapters", response_model=dict)
def save_chapter(request: SaveChapterRequest):
    """Save a new chapter."""
    chapter_id = content_service.save_chapter(
        user_id=request.user_id,
        chapter_number=request.chapter_number,
        title=request.title,
        description=request.description,
        theme=request.theme,
        theme_description=request.theme_description,
        weeks_start=request.weeks_start,
        weeks_end=request.weeks_end,
    )
    return {"id": chapter_id}


@router.get("/users/{user_id}/chapters", response_model=list[ChapterResponse])
def get_chapters(user_id: UUID):
    """Get all chapters for a user."""
    return content_service.get_chapters(user_id)


@router.get("/chapters/{chapter_id}", response_model=ChapterResponse)
def get_chapter(chapter_id: UUID):
    """Get a single chapter."""
    chapter = content_service.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


# =============================================================================
# Post Endpoints
# =============================================================================


@router.post("/posts", response_model=dict)
def save_post(request: SavePostRequest):
    """Save a new post."""
    post_id = content_service.save_post(
        user_id=request.user_id,
        chapter_id=request.chapter_id,
        post_number=request.post_number,
        topic=request.topic,
        shape=request.shape,
        cadence=request.cadence,
        entry_point=request.entry_point,
        status=request.status,
        guidance=request.guidance,
    )
    return {"id": post_id}


@router.get("/users/{user_id}/posts", response_model=list[PostResponse])
def get_posts(
    user_id: UUID,
    chapter_id: Optional[UUID] = None,
    status: Optional[str] = None,
):
    """Get posts for a user, optionally filtered."""
    return content_service.get_posts(user_id, chapter_id=chapter_id, status=status)


@router.get("/users/{user_id}/posts/available", response_model=list[PostResponse])
def get_available_posts(user_id: UUID):
    """Get posts that need work."""
    return content_service.get_available_posts(user_id)


@router.get("/users/{user_id}/posts/next", response_model=PostResponse)
def get_next_post(user_id: UUID):
    """Get the next unfinished post."""
    post = content_service.get_next_post(user_id)
    if not post:
        raise HTTPException(status_code=404, detail="No available posts")
    return post


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: UUID):
    """Get a single post."""
    post = content_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.put("/posts/{post_id}")
def update_post(post_id: UUID, request: UpdatePostRequest):
    """Update post fields."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    content_service.update_post(post_id, **updates)
    return {"status": "updated"}


class UpdatePostStatusRequest(BaseModel):
    status: str


@router.post("/posts/{story_id}/status")
def update_post_status_by_story(
    story_id: str,
    request: UpdatePostStatusRequest,
    user_id: Optional[UUID] = None,
):
    """Update post status by story ID (e.g., 'post_04')."""
    match = re.search(r"post_(\d+)", story_id)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid story ID format. Expected 'post_XX'")

    post_number = int(match.group(1))
    post = content_service.get_post_by_number(user_id, post_number)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_number} not found")

    content_service.update_post(post.id, status=request.status)
    return {"status": "updated", "post_id": post.id, "new_status": request.status}


@router.post("/posts/{story_id}/reset")
def reset_post(
    story_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Reset a post to 'not started' state.

    This will:
    - Set status to 'not_started'
    - Delete final content file if exists
    - Delete any associated image prompts
    """
    user_id = current_user.user_id

    # Parse story_id (e.g., "post_04" or "c1p4")
    post_number = None
    if story_id.startswith("post_"):
        try:
            post_number = int(story_id.replace("post_", "").lstrip("0") or "0")
        except ValueError:
            pass
    elif story_id.startswith("c") and "p" in story_id:
        try:
            post_number = int(story_id.split("p")[1])
        except (ValueError, IndexError):
            pass

    if post_number is None:
        raise HTTPException(status_code=400, detail="Invalid story ID format")

    # Find the post
    post = content_service.get_post_by_number(user_id, post_number)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_number} not found")

    # Reset status
    content_service.update_post(post.id, status="not_started")

    # Delete final content file
    workflow_dir = Path("workflow")
    final_dir = workflow_dir / "final"
    deleted_files = []

    # Try various file patterns
    patterns = [
        f"post_{post_number:02d}.md",
        f"post_{post_number}.md",
        f"c*p{post_number}.md",
        f"c*p{post_number:02d}.md",
    ]

    for pattern in patterns:
        for f in final_dir.glob(pattern):
            f.unlink()
            deleted_files.append(str(f))

    # Delete drafts too
    drafts_dir = workflow_dir / "drafts"
    for pattern in patterns:
        for f in drafts_dir.glob(pattern):
            f.unlink()
            deleted_files.append(str(f))

    # Delete image prompts for this post
    image_service = ImagePromptService()
    prompts = image_service.get_prompts(user_id, story_id)
    for prompt in prompts:
        image_service.delete_prompt(prompt.id)

    return {
        "status": "reset",
        "post_id": post.id,
        "post_number": post_number,
        "deleted_files": deleted_files,
        "deleted_prompts": len(prompts),
    }


# =============================================================================
# Writing Sample Endpoints
# =============================================================================


@router.post("/samples", response_model=dict)
def save_writing_sample(request: SaveWritingSampleRequest):
    """Save a writing sample."""
    sample_id = content_service.save_writing_sample(
        user_id=request.user_id,
        source_type=request.source_type,
        content=request.content,
        prompt_id=request.prompt_id,
        prompt_text=request.prompt_text,
        title=request.title,
    )
    return {"id": sample_id}


@router.get("/users/{user_id}/samples", response_model=list[WritingSampleRecord])
def get_writing_samples(user_id: UUID):
    """Get all writing samples for a user."""
    return content_service.get_writing_samples(user_id)


# =============================================================================
# Voice Profile Endpoints
# =============================================================================


@router.post("/voice-profiles", response_model=dict)
def save_voice_profile(request: SaveVoiceProfileRequest):
    """Save a voice profile."""
    profile_id = content_service.save_voice_profile(
        user_id=request.user_id,
        tone=request.tone,
        sentence_patterns=request.sentence_patterns,
        vocabulary_level=request.vocabulary_level,
        signature_phrases=request.signature_phrases,
        storytelling_style=request.storytelling_style,
        emotional_register=request.emotional_register,
        raw_analysis=request.raw_analysis,
    )
    return {"id": profile_id}


@router.get("/users/{user_id}/voice-profile", response_model=VoiceProfileResponse)
def get_voice_profile(user_id: UUID):
    """Get user's voice profile."""
    profile = content_service.get_voice_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    return profile


@router.put("/voice-profiles/{profile_id}")
def update_voice_profile(profile_id: UUID, request: UpdateVoiceProfileRequest):
    """Update voice profile fields."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    content_service.update_voice_profile(profile_id, **updates)
    return {"status": "updated"}


# =============================================================================
# Constants Endpoints
# =============================================================================


@router.get("/prompts")
def get_voice_prompts():
    """Get available voice learning prompts."""
    return {"prompts": ContentService.get_voice_prompts()}


@router.get("/styles")
def get_content_styles():
    """Get available content styles."""
    return {"styles": ContentService.get_content_styles()}


@router.get("/shapes")
def get_post_shapes():
    """Get available post shapes."""
    return {"shapes": ContentService.get_post_shapes()}
