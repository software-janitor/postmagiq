"""API routes for workflow configuration.

Owner-only access - these are internal backend configuration endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.auth.dependencies import CurrentUser, require_owner_role
from api.models.api_models import ConfigUpdateRequest, ConfigValidationResult
from api.services.config_service import ConfigService

router = APIRouter()
config_service = ConfigService()


@router.get("")
async def get_config(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Get current workflow configuration as YAML."""
    return {"config": config_service.get_config_yaml()}


@router.put("")
async def update_config(
    request: ConfigUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Update workflow configuration."""
    valid, errors, warnings = config_service.validate_config(request.config)
    if not valid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid configuration", "errors": errors},
        )

    try:
        config_service.save_config(request.config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")

    return {"status": "saved", "warnings": warnings}


@router.post("/validate", response_model=ConfigValidationResult)
async def validate_config(
    request: ConfigUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Validate configuration without saving."""
    valid, errors, warnings = config_service.validate_config(request.config)
    return ConfigValidationResult(valid=valid, errors=errors, warnings=warnings)


@router.get("/agents")
async def get_agents(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Get list of available agents."""
    return {"agents": config_service.get_agents()}


@router.get("/personas")
async def get_personas(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Get list of available personas."""
    return {"personas": config_service.get_personas()}


@router.get("/states")
async def get_workflow_states(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Get workflow states with their agents for the UI."""
    return {"states": config_service.get_workflow_states()}
