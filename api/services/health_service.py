"""Health check service for component status monitoring.

Provides methods to check the health of various system components:
- Database connectivity
- Redis connectivity (if applicable)
- Detailed health status
"""

import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ComponentHealth(BaseModel):
    """Health status for a single component."""
    name: str
    status: str  # "healthy", "unhealthy", "degraded"
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class DetailedHealth(BaseModel):
    """Detailed health status with all component statuses."""
    status: str  # "healthy", "unhealthy", "degraded"
    timestamp: str
    version: str
    components: list[ComponentHealth]


class HealthService:
    """Service for checking system component health."""

    def __init__(self, version: str = "1.0.0"):
        self.version = version

    def check_database(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is accessible, False otherwise.
        """
        try:
            from runner.db.engine import engine
            from sqlmodel import Session, text

            if engine is None:
                logger.warning("Database engine not initialized")
                return False

            with Session(engine) as session:
                # Simple query to verify connectivity
                result = session.exec(text("SELECT 1"))
                result.fetchone()
                return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def check_redis(self) -> bool:
        """Check Redis connectivity (placeholder for future implementation).

        Returns:
            True if Redis is accessible, False otherwise.
            Currently returns True as Redis is not yet implemented.
        """
        # Redis not implemented yet - return True to indicate not blocking
        return True

    def get_detailed_health(self) -> DetailedHealth:
        """Get detailed health status of all components.

        Returns:
            DetailedHealth with status of each component.
        """
        components = []
        overall_status = "healthy"

        # Check database
        db_start = datetime.now()
        db_healthy = self.check_database()
        db_latency = (datetime.now() - db_start).total_seconds() * 1000

        components.append(
            ComponentHealth(
                name="database",
                status="healthy" if db_healthy else "unhealthy",
                latency_ms=round(db_latency, 2),
                message=None if db_healthy else "Database connection failed",
            )
        )

        if not db_healthy:
            overall_status = "unhealthy"

        # Check Redis (placeholder)
        redis_healthy = self.check_redis()
        components.append(
            ComponentHealth(
                name="redis",
                status="healthy" if redis_healthy else "unhealthy",
                latency_ms=None,  # No actual check yet
                message="Not implemented" if redis_healthy else "Redis connection failed",
            )
        )

        # If any critical component is unhealthy, overall is unhealthy
        # If any component is degraded but none unhealthy, overall is degraded
        unhealthy_count = sum(1 for c in components if c.status == "unhealthy")
        if unhealthy_count > 0:
            overall_status = "unhealthy"

        return DetailedHealth(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            version=self.version,
            components=components,
        )
