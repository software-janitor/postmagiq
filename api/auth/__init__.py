"""Authentication and authorization module for the API."""

from api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from api.auth.password import hash_password, verify_password
from api.auth.scopes import Scope, ROLE_SCOPES, has_scope, get_scopes_for_role
from api.auth.dependencies import (
    CurrentUser,
    get_current_user,
    require_scope,
    require_any_scope,
    require_all_scopes,
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    # Password
    "hash_password",
    "verify_password",
    # Scopes
    "Scope",
    "ROLE_SCOPES",
    "has_scope",
    "get_scopes_for_role",
    # Dependencies
    "CurrentUser",
    "get_current_user",
    "require_scope",
    "require_any_scope",
    "require_all_scopes",
]
