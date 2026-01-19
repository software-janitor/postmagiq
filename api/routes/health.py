"""Health check API routes.

Provides endpoints for:
- GET /health - Basic liveness check
- GET /health/ready - Readiness check (DB connectivity)
- GET /health/detailed - Detailed health with component status (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth.dependencies import CurrentUser, require_scope
from api.auth.scopes import Scope
from api.services.health_service import DetailedHealth, HealthService

router = APIRouter(prefix="/health", tags=["health"])

# Shared health service instance
health_service = HealthService()


@router.get("")
async def health() -> dict:
    """Basic liveness check.

    Returns 200 if the service is running.
    No authentication required.

    Returns:
        dict: {"status": "ok"}
    """
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    """Readiness check.

    Verifies the service is ready to handle requests by checking
    critical dependencies (database connectivity).
    No authentication required.

    Returns:
        dict: {"status": "ok", "database": true/false}

    Raises:
        HTTPException 503: Service not ready
    """
    db_healthy = health_service.check_database()

    if not db_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready: database unavailable",
        )

    return {
        "status": "ok",
        "database": db_healthy,
    }


@router.get("/detailed", response_model=DetailedHealth)
async def detailed(
    current_user: CurrentUser = Depends(require_scope(Scope.ADMIN)),
) -> DetailedHealth:
    """Detailed health check with component status.

    Returns comprehensive health information including latency
    measurements for each component. Requires admin scope.

    Returns:
        DetailedHealth: Full health status of all components

    Raises:
        HTTPException 401: Not authenticated
        HTTPException 403: Missing admin scope
    """
    return health_service.get_detailed_health()
