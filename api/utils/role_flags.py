"""Role-based feature flags for user experience customization.

Flags are tied to roles, not individual users. This keeps the system simple
and predictable while allowing different experiences for different user types.

Roles:
- owner: Full access to all features, internal views, actual costs
- admin: Extended access (future use)
- user: Simplified experience, credit-based usage, no internal tooling
"""

from typing import TypedDict

from runner.db.models import UserRole


class RoleFlags(TypedDict):
    """Type definition for role-based feature flags."""

    # UI visibility flags
    show_internal_workflow: bool  # State machine internals, agent logs
    show_image_tools: bool  # Outfit bank, characters, image config
    show_ai_personas: bool  # AI persona management
    show_live_workflow: bool  # Live workflow visualization
    show_state_editor: bool  # State editor for debugging
    show_approvals: bool  # Approval workflow UI
    show_teams: bool  # Team management UI
    show_strategy_admin: bool  # Strategy admin tools

    # Display mode flags
    show_costs: bool  # True = show actual $ costs, False = show credits

    # Behavior limits
    max_circuit_breaker: int  # Max retries for workflow circuit breaker


ROLE_FLAGS: dict[str, RoleFlags] = {
    "owner": {
        "show_internal_workflow": True,
        "show_image_tools": True,
        "show_ai_personas": True,
        "show_live_workflow": True,
        "show_state_editor": True,
        "show_approvals": True,
        "show_teams": True,
        "show_strategy_admin": True,
        "show_costs": True,
        "max_circuit_breaker": 3,
    },
    "admin": {
        "show_internal_workflow": False,
        "show_image_tools": True,
        "show_ai_personas": False,
        "show_live_workflow": False,
        "show_state_editor": False,
        "show_approvals": True,
        "show_teams": True,
        "show_strategy_admin": False,
        "show_costs": False,
        "max_circuit_breaker": 2,
    },
    "user": {
        "show_internal_workflow": False,
        "show_image_tools": False,
        "show_ai_personas": False,
        "show_live_workflow": False,
        "show_state_editor": False,
        "show_approvals": False,
        "show_teams": False,
        "show_strategy_admin": False,
        "show_costs": False,
        "max_circuit_breaker": 1,
    },
}


def get_flags_for_role(role: UserRole) -> RoleFlags:
    """Get feature flags for a given user role.

    Args:
        role: The user's role (owner, admin, or user)

    Returns:
        Dictionary of feature flags for the role
    """
    # Handle both enum and string values
    role_key = role.value if hasattr(role, 'value') else role
    return ROLE_FLAGS.get(role_key, ROLE_FLAGS["user"])


def get_flags_for_user(user) -> RoleFlags:
    """Get feature flags for a user based on their role.

    Args:
        user: User object with a role attribute

    Returns:
        Dictionary of feature flags for the user's role
    """
    return get_flags_for_role(user.role)
