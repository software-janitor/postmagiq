"""FastAPI backend for Workflow Orchestrator GUI."""

import logging

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# Note: deprecated routes moved to api/routes/deprecated/ - see README.md there
from api.routes import (
    runs,
    workflow,
    config,
    ws,
    workflow_personas,
    auth,
    health,
    portal,
    workflow_configs,
)
from api.routes.v1 import (
    workspaces_router,
    content_router,
    usage_router,
    billing_router,
    webhook_router,
    approvals_router,
    notifications_router,
    api_keys_router,
    webhooks_router,
    audit_router,
    domains_router,
    privacy_router,
    voice_profiles_router,
    voice_router,
    onboarding_router,
    finished_posts_router,
    transcription_router,
)
from api.routes.deprecated import finished_posts as deprecated_finished_posts
from api.middleware import (
    UsageEnforcementMiddleware,
    MetricsMiddleware,
    get_metrics,
    get_metrics_content_type,
    AuthMiddleware,
    WorkspaceMiddleware,
    CustomDomainMiddleware,
)
from api.error_handlers import register_error_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


app = FastAPI(
    title="Workflow Orchestrator API",
    description="API for workflow visualization and control",
    version="1.0.0",
)

# Middleware is added in reverse order of execution
# Order of execution: CORS -> CustomDomain -> Auth -> Workspace -> Metrics -> Usage -> Route
# Therefore add_middleware calls are in reverse order

# Usage enforcement middleware (closest to route handlers)
app.add_middleware(UsageEnforcementMiddleware)

# Metrics middleware (captures all request metrics)
app.add_middleware(MetricsMiddleware)

# Workspace middleware (validates workspace membership, requires Auth to run first)
app.add_middleware(WorkspaceMiddleware)

# Auth middleware (extracts user from JWT, required by Workspace middleware)
app.add_middleware(AuthMiddleware)

# Custom domain middleware (handles white-label domain routing)
app.add_middleware(CustomDomainMiddleware)

# CORS for React dev server (outermost - handles preflight requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global error handlers
register_error_handlers(app)

# Register core routes (MVP)
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(ws.router, prefix="/api/ws", tags=["websocket"])
app.include_router(workflow_personas.router, prefix="/api", tags=["workflow-personas"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(
    workflow_configs.router, prefix="/api/workflow-configs", tags=["workflow-configs"]
)

# v1 routes with workspace scoping
app.include_router(workspaces_router, prefix="/api", tags=["workspaces"])
app.include_router(content_router, prefix="/api", tags=["workspace-content"])
app.include_router(usage_router, prefix="/api", tags=["usage"])
app.include_router(billing_router, prefix="/api", tags=["billing"])
app.include_router(webhook_router, prefix="/api", tags=["stripe-webhooks"])
app.include_router(approvals_router, prefix="/api", tags=["approvals"])
app.include_router(notifications_router, prefix="/api", tags=["notifications"])
app.include_router(api_keys_router, prefix="/api", tags=["api-keys"])
app.include_router(webhooks_router, prefix="/api", tags=["webhooks"])
app.include_router(audit_router, prefix="/api", tags=["audit"])
app.include_router(domains_router, prefix="/api", tags=["domains"])
app.include_router(privacy_router, prefix="/api", tags=["privacy"])
app.include_router(voice_profiles_router, prefix="/api", tags=["voice-profiles"])
app.include_router(voice_router, prefix="/api", tags=["voice"])
app.include_router(onboarding_router, prefix="/api", tags=["onboarding-v1"])
app.include_router(finished_posts_router, prefix="/api", tags=["finished-posts-v1"])
app.include_router(transcription_router, prefix="/api", tags=["transcription"])

# Deprecated routes (for backwards compatibility)
app.include_router(
    deprecated_finished_posts.router, prefix="/api", tags=["finished-posts-deprecated"]
)

# Client portal routes (public login + authenticated review)
app.include_router(portal.router, prefix="/api", tags=["portal"])

# Health check routes (no auth required for basic health endpoints)
app.include_router(health.router, prefix="/api", tags=["health"])


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint for scraping."""
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )
