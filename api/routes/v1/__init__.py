"""v1 API routes with workspace scoping.

All routes in this module follow the pattern:
/api/v1/w/{workspace_id}/...

This ensures proper multi-tenancy by including workspace context in the URL.

User-level routes (not workspace-scoped) use:
/api/v1/users/me/...
"""

from api.routes.v1.workspaces import router as workspaces_router
from api.routes.v1.workspace_content import router as content_router
from api.routes.v1.usage import router as usage_router
from api.routes.v1.billing import router as billing_router, webhook_router
from api.routes.v1.approvals import router as approvals_router
from api.routes.v1.notifications import router as notifications_router
from api.routes.v1.api_keys import router as api_keys_router
from api.routes.v1.webhooks import router as webhooks_router
from api.routes.v1.audit import router as audit_router
from api.routes.v1.domains import router as domains_router
from api.routes.v1.privacy import router as privacy_router
from api.routes.v1.voice_profiles import router as voice_profiles_router
from api.routes.v1.voice import router as voice_router
from api.routes.v1.onboarding import router as onboarding_router
from api.routes.v1.finished_posts import router as finished_posts_router

__all__ = [
    "workspaces_router",
    "content_router",
    "usage_router",
    "billing_router",
    "webhook_router",
    "approvals_router",
    "notifications_router",
    "api_keys_router",
    "webhooks_router",
    "audit_router",
    "domains_router",
    "privacy_router",
    "voice_profiles_router",
    "voice_router",
    "onboarding_router",
    "finished_posts_router",
]
