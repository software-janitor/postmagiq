"""API routes for workflow configuration selection.

Provides endpoints for listing and selecting workflow configurations
for the GUI workflow selector.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from api.auth.dependencies import CurrentUser, get_current_user
from runner.db.engine import engine
from runner.db.models import WorkflowConfigRead, WorkflowEnvironment
from runner.content.workflow_config_repository import WorkflowConfigRepository


router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class WorkflowConfigListResponse(BaseModel):
    """Response for listing workflow configs."""

    configs: list[WorkflowConfigRead]
    default_slug: Optional[str] = None


class WorkflowConfigResponse(BaseModel):
    """Response for a single workflow config."""

    config: WorkflowConfigRead


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=WorkflowConfigListResponse)
async def list_workflow_configs(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    environment: Optional[WorkflowEnvironment] = Query(
        None, description="Filter by environment (production, development, staging)"
    ),
    enabled_only: bool = Query(True, description="Only return enabled configs"),
):
    """List available workflow configurations.

    Returns workflow configs that the user can select from.
    Optionally filter by environment.
    """
    with Session(engine) as session:
        repo = WorkflowConfigRepository(session)

        if environment:
            configs = repo.list_by_environment(environment)
        elif enabled_only:
            configs = repo.list_enabled()
        else:
            configs = repo.list_all()

        # Get default config
        default_config = repo.get_default()
        default_slug = default_config.slug if default_config else None

        # Convert to read models
        config_reads = [WorkflowConfigRead.model_validate(c) for c in configs]

        return WorkflowConfigListResponse(
            configs=config_reads,
            default_slug=default_slug,
        )


@router.get("/{slug}", response_model=WorkflowConfigResponse)
async def get_workflow_config(
    slug: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get a specific workflow configuration by slug.

    Returns the workflow config details including features and tier requirements.
    """
    with Session(engine) as session:
        repo = WorkflowConfigRepository(session)
        config = repo.get_by_slug(slug)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow config not found: {slug}",
            )

        if not config.enabled:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow config is disabled: {slug}",
            )

        return WorkflowConfigResponse(
            config=WorkflowConfigRead.model_validate(config),
        )


@router.get("/default", response_model=WorkflowConfigResponse)
async def get_default_workflow_config(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get the default workflow configuration.

    Returns the workflow config marked as default, or 404 if none is set.
    """
    with Session(engine) as session:
        repo = WorkflowConfigRepository(session)
        config = repo.get_default()

        if not config:
            raise HTTPException(
                status_code=404,
                detail="No default workflow config is set",
            )

        return WorkflowConfigResponse(
            config=WorkflowConfigRead.model_validate(config),
        )
