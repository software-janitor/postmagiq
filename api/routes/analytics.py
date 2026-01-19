"""API routes for analytics import and querying."""

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from api.services.analytics_service import AnalyticsService
from runner.content.models import (
    AnalyticsImportResponse,
    PostMetricResponse,
    AnalyticsSummary,
    DailyMetricResponse,
    FollowerMetricResponse,
    AudienceDemographicResponse,
    PostDemographicResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])
analytics_service = AnalyticsService()


# =============================================================================
# Request/Response Models
# =============================================================================


class ImportResponse(BaseModel):
    """Response for analytics import."""
    import_id: str
    success: bool
    rows_imported: Optional[int] = None
    error: Optional[str] = None


class ImportsListResponse(BaseModel):
    """List of imports."""
    imports: list[AnalyticsImportResponse]


class MetricsListResponse(BaseModel):
    """List of metrics."""
    metrics: list[PostMetricResponse]


class TopPostsResponse(BaseModel):
    """Top performing posts."""
    posts: list[PostMetricResponse]


# =============================================================================
# Import Endpoints
# =============================================================================


@router.post("/import", response_model=ImportResponse)
async def import_analytics(
    user_id: str = Form(...),
    platform: str = Form(...),  # 'linkedin', 'threads', 'x'
    file: UploadFile = File(...),
):
    """Import analytics from a CSV or Excel file.

    Supported platforms:
    - linkedin: LinkedIn Analytics export (CSV or XLS)
    - threads: Threads/Meta analytics
    - x/twitter: X/Twitter analytics export

    Supported file formats: .csv, .xls, .xlsx
    """
    # Validate platform
    valid_platforms = ["linkedin", "threads", "x", "twitter"]
    if platform.lower() not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}",
        )

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    filename = file.filename or "upload.csv"

    # Create import record
    import_id = analytics_service.create_import(
        user_id=user_id,
        platform_name=platform.lower(),
        filename=filename,
    )

    # Process file (handles both CSV and XLS/XLSX)
    result = analytics_service.process_file(
        user_id=user_id,
        import_id=import_id,
        platform_name=platform.lower(),
        file_content=content,
        filename=filename,
    )

    return ImportResponse(
        import_id=import_id,
        success=result["success"],
        rows_imported=result.get("rows_imported"),
        error=result.get("error"),
    )


@router.get("/users/{user_id}/imports", response_model=ImportsListResponse)
def get_imports(user_id: str):
    """Get all analytics imports for a user."""
    imports = analytics_service.get_imports(user_id)
    return ImportsListResponse(imports=imports)


@router.delete("/users/{user_id}/clear")
def clear_analytics(user_id: str):
    """Clear all analytics data for a user.

    This will delete:
    - All analytics imports
    - All post metrics
    - All daily metrics
    - All follower metrics
    - All audience demographics
    - All post demographics

    Use this to start fresh before reimporting data.
    """
    result = analytics_service.clear_analytics(user_id)
    return {
        "success": True,
        "message": "All analytics data cleared",
        "deleted": result,
    }


# =============================================================================
# Query Endpoints
# =============================================================================


@router.get("/users/{user_id}/metrics", response_model=MetricsListResponse)
def get_metrics(
    user_id: str,
    platform: Optional[str] = None,
    limit: int = 100,
):
    """Get analytics metrics for a user.

    Args:
        user_id: User ID
        platform: Optional platform filter (linkedin, threads, x)
        limit: Maximum number of results (default 100)
    """
    metrics = analytics_service.get_metrics(user_id, platform, limit)
    return MetricsListResponse(metrics=metrics)


@router.get("/users/{user_id}/top-posts", response_model=TopPostsResponse)
def get_top_posts(
    user_id: str,
    metric: str = "impressions",
    limit: int = 10,
):
    """Get top performing posts by a specific metric.

    Args:
        user_id: User ID
        metric: Metric to sort by (impressions, engagement_count, likes, etc.)
        limit: Number of posts to return (default 10)
    """
    valid_metrics = ["impressions", "engagement_count", "engagement_rate", "likes", "comments", "shares", "clicks"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
        )

    posts = analytics_service.get_top_posts(user_id, metric, limit)
    return TopPostsResponse(posts=posts)


@router.get("/users/{user_id}/summary", response_model=AnalyticsSummary)
def get_summary(
    user_id: str,
    platform: Optional[str] = None,
):
    """Get analytics summary for a user.

    Returns aggregate statistics including:
    - Total impressions, engagements, likes, comments, shares, clicks
    - Average engagement rate
    - Top performing posts
    """
    return analytics_service.get_summary(user_id, platform)


# =============================================================================
# Daily Metrics Endpoints
# =============================================================================


class DailyMetricsResponse(BaseModel):
    """Daily metrics list."""
    metrics: list[DailyMetricResponse]


@router.get("/users/{user_id}/daily", response_model=DailyMetricsResponse)
def get_daily_metrics(
    user_id: str,
    platform: Optional[str] = None,
    limit: int = 90,
):
    """Get daily aggregate metrics for time series charts.

    Args:
        user_id: User ID
        platform: Optional platform filter
        limit: Maximum days to return (default 90)
    """
    metrics = analytics_service.get_daily_metrics(user_id, platform, limit)
    return DailyMetricsResponse(metrics=metrics)


# =============================================================================
# Follower Metrics Endpoints
# =============================================================================


class FollowerMetricsResponse(BaseModel):
    """Follower metrics list."""
    metrics: list[FollowerMetricResponse]
    latest_total: Optional[int] = None


@router.get("/users/{user_id}/followers", response_model=FollowerMetricsResponse)
def get_follower_metrics(
    user_id: str,
    platform: Optional[str] = None,
    limit: int = 90,
):
    """Get follower metrics for time series charts.

    Args:
        user_id: User ID
        platform: Optional platform filter
        limit: Maximum days to return (default 90)
    """
    metrics = analytics_service.get_follower_metrics(user_id, platform, limit)
    latest = analytics_service.get_latest_follower_count(user_id, platform or "linkedin")
    return FollowerMetricsResponse(metrics=metrics, latest_total=latest)


# =============================================================================
# Demographics Endpoints
# =============================================================================


class AudienceDemographicsResponse(BaseModel):
    """Audience demographics list."""
    demographics: list[AudienceDemographicResponse]


class PostDemographicsResponse(BaseModel):
    """Post demographics list."""
    demographics: list[PostDemographicResponse]


@router.get("/users/{user_id}/demographics", response_model=AudienceDemographicsResponse)
def get_audience_demographics(
    user_id: str,
    platform: Optional[str] = None,
    category: Optional[str] = None,
):
    """Get audience demographics breakdown.

    Args:
        user_id: User ID
        platform: Optional platform filter
        category: Optional category filter (job_title, location, industry, seniority, company_size)
    """
    valid_categories = ["job_title", "job_function", "location", "industry", "seniority", "company_size"]
    if category and category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}",
        )

    demographics = analytics_service.get_audience_demographics(user_id, platform, category)
    return AudienceDemographicsResponse(demographics=demographics)


@router.get("/users/{user_id}/posts/demographics", response_model=PostDemographicsResponse)
def get_post_demographics(
    user_id: str,
    url: str,
):
    """Get demographics for a specific post.

    Args:
        user_id: User ID
        url: The external URL of the post
    """
    demographics = analytics_service.get_post_demographics(user_id, url)
    return PostDemographicsResponse(demographics=demographics)
