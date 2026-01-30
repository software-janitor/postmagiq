"""API routes for onboarding flow."""

from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import CurrentUser, get_current_user
from api.services.content_service import ContentService
from api.services.onboarding_service import (
    OnboardingService,
    QuickOnboardingAnswers,
    DeepModeState,
    GeneratedPlan,
)
from runner.db.models import UserRole

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
onboarding_service = OnboardingService()
content_service = ContentService()


def _verify_user_access(current_user: CurrentUser, target_user_id: UUID) -> None:
    """Verify user can access the target user's data."""
    is_owner = current_user.user.role == UserRole.owner
    if str(current_user.user_id) != str(target_user_id) and not is_owner:
        raise HTTPException(status_code=404, detail="Resource not found")


# =============================================================================
# Request Models
# =============================================================================


class StartRequest(BaseModel):
    """Start onboarding - creates user."""

    name: str
    email: Optional[str] = None


class QuickModeRequest(BaseModel):
    """Quick mode answers."""

    user_id: UUID
    professional_role: str
    known_for: str
    target_audience: str
    content_style: str
    posts_per_week: int


class DeepModeMessageRequest(BaseModel):
    """User message in deep mode conversation."""

    user_id: UUID
    message: str
    state: Optional[DeepModeState] = None  # Pass state for continuation
    force_ready: bool = False  # User can manually trigger generation readiness


class GeneratePlanRequest(BaseModel):
    """Request to generate plan from deep mode."""

    user_id: UUID
    content_style: str
    state: DeepModeState


class ApprovePlanRequest(BaseModel):
    """Approve and save generated plan."""

    user_id: UUID
    plan: dict  # GeneratedPlan as dict
    positioning: str
    target_audience: str
    content_style: str
    onboarding_mode: str
    transcript: Optional[str] = None
    workspace_id: Optional[UUID] = None


# =============================================================================
# Response Models
# =============================================================================


class StartResponse(BaseModel):
    """Response from starting onboarding."""

    user_id: str
    questions: list[dict]


class QuickModeResponse(BaseModel):
    """Response from quick mode - generated plan."""

    plan: GeneratedPlan


class DeepModeResponse(BaseModel):
    """Response from deep mode - assistant message + state."""

    assistant_message: str
    state: DeepModeState
    ready_to_generate: bool


class ApproveResponse(BaseModel):
    """Response from plan approval."""

    goal_id: str
    chapter_count: int
    post_count: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/strategy/{user_id}")
def get_existing_strategy(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    platform_id: Optional[UUID] = None,
):
    """Get existing strategy for a user, optionally filtered by platform."""
    _verify_user_access(current_user, user_id)

    goal = content_service.get_goal(user_id, platform_id=platform_id)
    if not goal:
        return {"exists": False}

    chapters = content_service.get_chapters(user_id, platform_id=platform_id)
    total_posts = sum(c.post_count for c in chapters)
    total_completed = sum(c.completed_count for c in chapters)

    return {
        "exists": True,
        "goal": {
            "id": goal.id,
            "strategy_type": goal.strategy_type,
            "positioning": goal.positioning,
            "signature_thesis": goal.signature_thesis,
            "target_audience": goal.target_audience,
            "content_style": goal.content_style,
            "onboarding_mode": goal.onboarding_mode,
        },
        "summary": {
            "total_chapters": len(chapters),
            "total_posts": total_posts,
            "completed_posts": total_completed,
            "weeks_total": chapters[-1].weeks_end if chapters else 0,
        },
        "chapters": [
            {
                "id": c.id,
                "chapter_number": c.chapter_number,
                "title": c.title,
                "description": c.description,
                "theme": c.theme,
                "theme_description": c.theme_description,
                "weeks_start": c.weeks_start,
                "weeks_end": c.weeks_end,
                "post_count": c.post_count,
                "completed_count": c.completed_count,
            }
            for c in chapters
        ],
    }


@router.post("/start", response_model=StartResponse)
def start_onboarding(
    request: StartRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Start onboarding flow - creates user and returns questions."""
    user_id = content_service.get_or_create_user(request.name, request.email)
    questions = OnboardingService.get_quick_mode_questions()
    return StartResponse(user_id=user_id, questions=questions)


@router.get("/questions")
def get_quick_questions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get quick mode questions."""
    return {"questions": OnboardingService.get_quick_mode_questions()}


# =============================================================================
# Quick Mode
# =============================================================================


@router.post("/quick", response_model=QuickModeResponse)
def quick_onboarding(
    request: QuickModeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Process quick mode answers and generate plan."""
    _verify_user_access(current_user, request.user_id)

    try:
        answers = QuickOnboardingAnswers(
            professional_role=request.professional_role,
            known_for=request.known_for,
            target_audience=request.target_audience,
            content_style=request.content_style,
            posts_per_week=request.posts_per_week,
        )
        plan = onboarding_service.generate_quick_plan(answers)
        return QuickModeResponse(plan=plan)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {e}")


# =============================================================================
# Deep Mode
# =============================================================================


@router.post("/deep/start", response_model=DeepModeResponse)
def start_deep_discovery(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Start deep discovery conversation."""
    try:
        state = onboarding_service.start_deep_discovery()
        return DeepModeResponse(
            assistant_message=state.messages[-1].content,
            state=state,
            ready_to_generate=state.ready_to_generate,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start discovery: {e}")


@router.post("/deep/message", response_model=DeepModeResponse)
def send_deep_message(
    request: DeepModeMessageRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Send message in deep discovery conversation.

    Set force_ready=true to manually trigger generation readiness
    (useful if LLM doesn't offer to generate after enough turns).
    """
    _verify_user_access(current_user, request.user_id)

    if not request.state:
        raise HTTPException(status_code=400, detail="State required for continuation")

    try:
        state = onboarding_service.continue_deep_discovery(
            request.state,
            request.message,
            force_ready=request.force_ready,
        )
        # If force_ready, last message is user's, not assistant's
        assistant_message = (
            state.messages[-1].content
            if state.messages[-1].role == "assistant"
            else "Ready to generate your content strategy!"
        )
        return DeepModeResponse(
            assistant_message=assistant_message,
            state=state,
            ready_to_generate=state.ready_to_generate,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to continue discovery: {e}"
        )


@router.post("/deep/generate", response_model=QuickModeResponse)
def generate_from_deep(
    request: GeneratePlanRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Generate plan from deep discovery conversation."""
    _verify_user_access(current_user, request.user_id)

    try:
        plan = onboarding_service.generate_deep_plan(
            request.state,
            request.content_style,
        )
        return QuickModeResponse(plan=plan)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {e}")


# =============================================================================
# Plan Approval
# =============================================================================


@router.post("/approve", response_model=ApproveResponse)
def approve_plan(
    request: ApprovePlanRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Approve and save generated plan to database."""
    _verify_user_access(current_user, request.user_id)

    try:
        plan = GeneratedPlan(**request.plan)
        goal_id = onboarding_service.save_plan(
            user_id=request.user_id,
            plan=plan,
            positioning=request.positioning,
            target_audience=request.target_audience,
            content_style=request.content_style,
            onboarding_mode=request.onboarding_mode,
            onboarding_transcript=request.transcript,
            workspace_id=request.workspace_id,
        )

        # Count chapters and posts
        chapter_count = len(plan.chapters)
        post_count = sum(len(c.get("posts", [])) for c in plan.chapters)

        return ApproveResponse(
            goal_id=goal_id,
            chapter_count=chapter_count,
            post_count=post_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save plan: {e}")
