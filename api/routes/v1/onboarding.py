"""Workspace-scoped onboarding/strategy routes.

All onboarding operations are scoped to a workspace.
Handles strategy creation via quick mode and deep mode conversations.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceCtx,
    WorkspaceContext,
    require_workspace_scope,
)
from api.services.content_service import ContentService
from api.services.onboarding_service import (
    OnboardingService,
    QuickOnboardingAnswers,
    DeepModeState,
    DeepModeMessage,
    GeneratedPlan,
)
from runner.db.engine import get_session_dependency


router = APIRouter(prefix="/v1/w/{workspace_id}/onboarding", tags=["onboarding"])
onboarding_service = OnboardingService()
content_service = ContentService()


# =============================================================================
# Request Models
# =============================================================================


class QuickModeRequest(BaseModel):
    """Quick mode answers."""

    professional_role: str
    known_for: str
    target_audience: str
    content_style: str
    posts_per_week: int


class DeepModeMessageRequest(BaseModel):
    """User message in deep mode conversation."""

    message: str
    state: Optional[DeepModeState] = None
    force_ready: bool = False


class GeneratePlanRequest(BaseModel):
    """Request to generate plan from deep mode."""

    content_style: str
    state: DeepModeState


class ApprovePlanRequest(BaseModel):
    """Approve and save generated plan."""

    plan: dict  # GeneratedPlan as dict
    positioning: str
    target_audience: str
    content_style: str
    onboarding_mode: str
    transcript: Optional[str] = None


# =============================================================================
# Response Models
# =============================================================================


class ContentStylesResponse(BaseModel):
    """Available content styles."""

    styles: list[dict]


class PostShapesResponse(BaseModel):
    """Available post shapes."""

    shapes: list[dict]


class QuickModeResponse(BaseModel):
    """Quick mode result."""

    plan: dict


class DeepModeResponse(BaseModel):
    """Deep mode conversation response."""

    message: str
    state: DeepModeState
    is_ready: bool


class PlanResponse(BaseModel):
    """Generated plan."""

    plan: dict


class ApproveResponse(BaseModel):
    """Plan approval result."""

    goal_id: str
    chapters: list[str]


class StrategyResponse(BaseModel):
    """Current strategy."""

    goal: Optional[dict]
    chapters: list[dict]


# =============================================================================
# Content Options
# =============================================================================


@router.get("/content-styles", response_model=ContentStylesResponse)
async def get_content_styles(
    ctx: WorkspaceCtx,
):
    """Get available content styles."""
    styles = content_service.get_content_styles()
    return ContentStylesResponse(styles=styles)


@router.get("/post-shapes", response_model=PostShapesResponse)
async def get_post_shapes(
    ctx: WorkspaceCtx,
):
    """Get available post shapes."""
    shapes = content_service.get_post_shapes()
    return PostShapesResponse(shapes=shapes)


# =============================================================================
# Quick Mode
# =============================================================================


@router.post("/quick", response_model=QuickModeResponse)
async def process_quick_mode(
    request: QuickModeRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))],
):
    """Process quick mode onboarding.

    Generates a content plan from structured answers.
    Requires strategy:write scope.
    """
    answers = QuickOnboardingAnswers(
        professional_role=request.professional_role,
        known_for=request.known_for,
        target_audience=request.target_audience,
        content_style=request.content_style,
        posts_per_week=request.posts_per_week,
    )

    try:
        plan = onboarding_service.generate_quick_mode_plan(answers)
        return QuickModeResponse(plan=plan.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate plan: {str(e)}",
        )


# =============================================================================
# Deep Mode
# =============================================================================


@router.post("/deep/message", response_model=DeepModeResponse)
async def send_deep_mode_message(
    request: DeepModeMessageRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))],
):
    """Send a message in deep mode conversation.

    Requires strategy:write scope.
    """
    try:
        result = onboarding_service.process_deep_mode_message(
            message=request.message,
            state=request.state,
            force_ready=request.force_ready,
        )
        return DeepModeResponse(
            message=result.response,
            state=result.state,
            is_ready=result.is_ready,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversation error: {str(e)}",
        )


@router.post("/deep/generate-plan", response_model=PlanResponse)
async def generate_plan_from_deep_mode(
    request: GeneratePlanRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))],
):
    """Generate content plan from deep mode conversation.

    Requires strategy:write scope.
    """
    try:
        plan = onboarding_service.generate_deep_mode_plan(
            state=request.state,
            content_style=request.content_style,
        )
        return PlanResponse(plan=plan.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate plan: {str(e)}",
        )


# =============================================================================
# Plan Approval
# =============================================================================


@router.post("/approve", response_model=ApproveResponse)
async def approve_plan(
    request: ApprovePlanRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))],
):
    """Approve and save generated plan.

    Creates goal and chapters in the database.
    Requires strategy:write scope.
    """
    try:
        plan = GeneratedPlan(**request.plan)

        goal_id = content_service.save_goal(
            user_id=ctx.user_id,
            positioning=request.positioning,
            target_audience=request.target_audience,
            content_style=request.content_style,
            onboarding_mode=request.onboarding_mode,
            transcript=request.transcript,
            workspace_id=ctx.workspace_id,
        )

        chapter_ids = []
        for chapter in plan.chapters:
            chapter_id = content_service.save_chapter(
                user_id=ctx.user_id,
                goal_id=goal_id,
                title=chapter.title,
                description=chapter.description,
                posts=chapter.posts,
                workspace_id=ctx.workspace_id,
            )
            chapter_ids.append(chapter_id)

        return ApproveResponse(
            goal_id=goal_id,
            chapters=chapter_ids,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save plan: {str(e)}",
        )


# =============================================================================
# Strategy Retrieval
# =============================================================================


@router.get("/strategy", response_model=StrategyResponse)
async def get_strategy(
    ctx: WorkspaceCtx,
):
    """Get current strategy for the workspace.

    Returns the goal and associated chapters.
    """
    goal = content_service.get_goal_for_workspace(ctx.workspace_id)
    chapters = content_service.get_chapters_for_workspace(ctx.workspace_id)

    return StrategyResponse(
        goal=goal,
        chapters=chapters,
    )


@router.delete("/strategy", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))],
):
    """Delete the current strategy.

    Removes goal and associated chapters.
    Requires strategy:write scope.
    """
    content_service.delete_strategy_for_workspace(ctx.workspace_id)
