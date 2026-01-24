"""FastAPI dependencies for authentication and authorization.

Provides:
- get_current_user: Extract and validate user from JWT token
- require_scope: Decorator/dependency to enforce RBAC scopes
"""

from functools import wraps
from typing import Callable, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth.jwt import verify_token, VALID_ACCESS_TOKEN_TYPES
from api.auth.scopes import Scope, has_scope
from runner.db.models import User, UserRole, WorkspaceMembership, WorkspaceRole


# Security scheme for JWT Bearer tokens
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Container for authenticated user context.

    Contains the user object and optional workspace membership
    when operating within a workspace context.
    """

    def __init__(
        self,
        user: User,
        membership: Optional[WorkspaceMembership] = None,
    ):
        self.user = user
        self.membership = membership

    @property
    def user_id(self) -> UUID:
        return self.user.id

    @property
    def role(self) -> Optional[WorkspaceRole]:
        return self.membership.role if self.membership else None

    def has_scope(self, scope: Scope) -> bool:
        """Check if user has scope in current workspace context."""
        if not self.membership:
            return False
        return has_scope(self.membership.role, scope)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """Extract and validate current user from JWT token.

    This dependency:
    1. Extracts JWT from Authorization header
    2. Verifies token validity
    3. Loads user from database
    4. Returns CurrentUser with user and optional membership

    The membership is set by WorkspaceMiddleware when operating
    within a workspace context (e.g., /api/v1/w/{workspace_id}/...).

    Raises:
        HTTPException 401: Missing or invalid token
        HTTPException 401: User not found

    Returns:
        CurrentUser: Authenticated user context
    """
    # Check if user was already set by AuthMiddleware
    if hasattr(request.state, "user") and request.state.user:
        membership = getattr(request.state, "membership", None)
        return CurrentUser(user=request.state.user, membership=membership)

    # Fall back to manual token extraction
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token type - only access tokens allowed for API routes
    token_type = payload.get("type", "access")
    if token_type not in VALID_ACCESS_TOKEN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for this endpoint",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user_id from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database
    from runner.db.engine import engine
    from sqlmodel import Session, select

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Store in request state for later use
        request.state.user = user
        request.state.jwt_claims = payload

        # Get membership from request state if set by WorkspaceMiddleware
        membership = getattr(request.state, "membership", None)
        return CurrentUser(user=user, membership=membership)


def require_scope(scope: Scope) -> Callable:
    """Create a dependency that checks if user has required scope.

    This is used as a FastAPI dependency to protect routes:

    ```python
    @router.post("/posts")
    async def create_post(
        current_user: CurrentUser = Depends(require_scope(Scope.CONTENT_WRITE))
    ):
        ...
    ```

    Args:
        scope: The required permission scope

    Returns:
        A FastAPI dependency that returns CurrentUser if authorized

    Raises:
        HTTPException 401: Not authenticated
        HTTPException 403: Missing required scope
    """

    async def scope_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        # Check if user has the required scope
        if not current_user.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {scope.value}",
            )
        return current_user

    return scope_checker


def require_any_scope(*scopes: Scope) -> Callable:
    """Create a dependency that checks if user has any of the specified scopes.

    Useful when multiple scopes can grant access to a resource.

    Args:
        *scopes: One or more scopes, any of which grants access

    Returns:
        A FastAPI dependency that returns CurrentUser if authorized
    """

    async def scope_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        for scope in scopes:
            if current_user.has_scope(scope):
                return current_user

        scope_names = ", ".join(s.value for s in scopes)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required scope. Need one of: {scope_names}",
        )

    return scope_checker


def require_all_scopes(*scopes: Scope) -> Callable:
    """Create a dependency that checks if user has all specified scopes.

    Useful when multiple permissions are required for an action.

    Args:
        *scopes: All scopes required for access

    Returns:
        A FastAPI dependency that returns CurrentUser if authorized
    """

    async def scope_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        missing = []
        for scope in scopes:
            if not current_user.has_scope(scope):
                missing.append(scope.value)

        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing)}",
            )
        return current_user

    return scope_checker


def require_owner_role() -> Callable:
    """Create a dependency that requires owner role.

    Use for internal/admin endpoints that should only be accessible
    to SaaS owners (e.g., workflow_personas, config management).

    Returns:
        A FastAPI dependency that returns CurrentUser if owner

    Raises:
        HTTPException 401: Not authenticated
        HTTPException 403: Not an owner
    """

    async def owner_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.user.role != UserRole.owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Owner access required",
            )
        return current_user

    return owner_checker
