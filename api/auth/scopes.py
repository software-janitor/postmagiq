"""RBAC scopes and role-to-scope mappings.

Defines permission scopes and maps workspace roles to their allowed scopes.
"""

from enum import Enum
from typing import FrozenSet

from runner.db.models import WorkspaceRole


class Scope(str, Enum):
    """Permission scopes for RBAC.

    Scopes follow the pattern: resource:action
    - content: posts, chapters, goals
    - strategy: voice profiles, content strategy settings
    - workflow: run workflows, view run history
    - team: workspace members
    - billing: subscription and payment management
    - admin: system-wide administration
    """

    # Content permissions
    CONTENT_READ = "content:read"
    CONTENT_WRITE = "content:write"
    CONTENT_APPROVE = "content:approve"

    # Strategy permissions
    STRATEGY_READ = "strategy:read"
    STRATEGY_WRITE = "strategy:write"

    # Workflow permissions
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_EXECUTE = "workflow:execute"

    # Team permissions
    TEAM_READ = "team:read"
    TEAM_MANAGE = "team:manage"

    # Billing permissions
    BILLING_READ = "billing:read"
    BILLING_MANAGE = "billing:manage"

    # Workspace permissions
    WORKSPACE_SETTINGS = "workspace:settings"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_USERS = "workspace:users"

    # Admin permissions (system-wide)
    ADMIN = "admin"


# Define scope sets for each role
_OWNER_SCOPES: FrozenSet[Scope] = frozenset(
    [
        Scope.CONTENT_READ,
        Scope.CONTENT_WRITE,
        Scope.CONTENT_APPROVE,
        Scope.STRATEGY_READ,
        Scope.STRATEGY_WRITE,
        Scope.WORKFLOW_READ,
        Scope.WORKFLOW_EXECUTE,
        Scope.TEAM_READ,
        Scope.TEAM_MANAGE,
        Scope.BILLING_READ,
        Scope.BILLING_MANAGE,
        Scope.WORKSPACE_SETTINGS,
        Scope.WORKSPACE_DELETE,
        Scope.WORKSPACE_USERS,
        Scope.ADMIN,
    ]
)

_ADMIN_SCOPES: FrozenSet[Scope] = frozenset(
    [
        Scope.CONTENT_READ,
        Scope.CONTENT_WRITE,
        Scope.CONTENT_APPROVE,
        Scope.STRATEGY_READ,
        Scope.STRATEGY_WRITE,
        Scope.WORKFLOW_READ,
        Scope.WORKFLOW_EXECUTE,
        Scope.TEAM_READ,
        Scope.TEAM_MANAGE,
        Scope.BILLING_READ,
        Scope.WORKSPACE_SETTINGS,
        Scope.WORKSPACE_USERS,
        # Note: admins cannot manage billing or delete workspace
    ]
)

_EDITOR_SCOPES: FrozenSet[Scope] = frozenset(
    [
        Scope.CONTENT_READ,
        Scope.CONTENT_WRITE,
        Scope.CONTENT_APPROVE,
        Scope.WORKFLOW_READ,
        Scope.WORKFLOW_EXECUTE,
        Scope.TEAM_READ,
        # Note: editors can view strategy but not edit it
        Scope.STRATEGY_READ,
    ]
)

_VIEWER_SCOPES: FrozenSet[Scope] = frozenset(
    [
        Scope.CONTENT_READ,
        Scope.STRATEGY_READ,
        Scope.WORKFLOW_READ,
        Scope.TEAM_READ,
        Scope.BILLING_READ,
    ]
)


ROLE_SCOPES: dict[WorkspaceRole, FrozenSet[Scope]] = {
    WorkspaceRole.owner: _OWNER_SCOPES,
    WorkspaceRole.admin: _ADMIN_SCOPES,
    WorkspaceRole.editor: _EDITOR_SCOPES,
    WorkspaceRole.viewer: _VIEWER_SCOPES,
}


def has_scope(role: WorkspaceRole, scope: Scope) -> bool:
    """Check if a role has a specific scope."""
    return scope in ROLE_SCOPES.get(role, frozenset())


def get_scopes_for_role(role: WorkspaceRole) -> FrozenSet[Scope]:
    """Get all scopes granted to a role."""
    return ROLE_SCOPES.get(role, frozenset())
