"""Evaluation API routes."""

from fastapi import APIRouter, HTTPException, Query

from api.services.eval_service import EvalService

router = APIRouter()
eval_service = EvalService()


@router.get("/agents")
async def get_agent_comparison(days: int = Query(30, ge=1, le=365)):
    """Get agent performance comparison over last N days.

    Args:
        days: Number of days to look back (1-365)

    Returns:
        Agent performance metrics including scores and sample sizes
    """
    return eval_service.get_agent_comparison(days)


@router.get("/costs")
async def get_cost_breakdown():
    """Get cost breakdown by agent.

    Returns:
        Total cost and per-agent breakdown with percentages
    """
    return eval_service.get_cost_breakdown()


@router.get("/trend")
async def get_quality_trend(weeks: int = Query(8, ge=1, le=52)):
    """Get quality score trend over last N weeks.

    Args:
        weeks: Number of weeks to include (1-52)

    Returns:
        Weekly quality scores, run counts, and costs
    """
    return eval_service.get_quality_trend(weeks)


@router.get("/daily")
async def get_daily_trend(days: int = Query(30, ge=1, le=90)):
    """Get daily quality trend.

    Args:
        days: Number of days to look back (1-90)

    Returns:
        Daily run counts, scores, and costs
    """
    return eval_service.get_daily_trend(days)


@router.get("/post/{story}")
async def get_post_iterations(story: str):
    """Get iteration history for a specific post.

    Args:
        story: Story identifier (e.g., "post_03")

    Returns:
        Iteration history with scores and improvements

    Raises:
        HTTPException: 404 if no iterations found
    """
    result = eval_service.get_post_iterations(story)
    if not result["iterations"]:
        raise HTTPException(404, f"No iterations found for story: {story}")
    return result


@router.get("/best/{state}")
async def get_best_agent_for_task(state: str):
    """Get best performing agent for a given task/state.

    Args:
        state: State name (e.g., "draft", "audit", "cross-audit")

    Returns:
        Ranked list of agents by performance on this task
    """
    result = eval_service.get_best_agent_for_task(state)
    return result


@router.get("/summary")
async def get_summary_stats():
    """Get high-level summary statistics.

    Returns:
        Overall stats including total runs, costs, and success rate
    """
    return eval_service.get_summary_stats()
