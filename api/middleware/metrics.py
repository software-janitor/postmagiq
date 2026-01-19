"""Prometheus metrics middleware for request monitoring.

Tracks:
- request_count: Counter by method, path, status
- request_latency: Histogram by method, path
- active_requests: Gauge of currently processing requests
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# Metrics definitions (created only if prometheus_client is available)
if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )

    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    ACTIVE_REQUESTS = Gauge(
        "http_requests_active",
        "Number of active HTTP requests",
    )


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests.

    Tracks request counts, latency histograms, and active request gauge.
    Metrics are exposed via the /metrics endpoint.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and record metrics.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            Response from downstream handler
        """
        if not PROMETHEUS_AVAILABLE:
            return await call_next(request)

        # Get normalized path (use route pattern, not actual path with IDs)
        path = self._get_path_template(request)
        method = request.method

        # Track active requests
        ACTIVE_REQUESTS.inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            ACTIVE_REQUESTS.dec()

            # Only record metrics for non-metrics endpoints
            if path != "/metrics" and path != "/api/metrics":
                REQUEST_COUNT.labels(
                    method=method,
                    path=path,
                    status=str(status_code),
                ).inc()

                REQUEST_LATENCY.labels(
                    method=method,
                    path=path,
                ).observe(duration)

        return response

    def _get_path_template(self, request: Request) -> str:
        """Get the route pattern instead of actual path.

        This normalizes paths like /api/users/123 to /api/users/{user_id}
        to prevent high cardinality in metrics labels.

        Args:
            request: HTTP request

        Returns:
            Route template pattern or actual path if no match
        """
        # Try to match against app routes
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path

        # Fall back to actual path if no route match
        return request.url.path


def get_metrics() -> bytes:
    """Generate Prometheus metrics output.

    Returns:
        Prometheus metrics in text format
    """
    if not PROMETHEUS_AVAILABLE:
        return b"# prometheus_client not installed\n"
    return generate_latest()


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics.

    Returns:
        Content-Type header value for Prometheus metrics
    """
    if not PROMETHEUS_AVAILABLE:
        return "text/plain"
    return CONTENT_TYPE_LATEST
