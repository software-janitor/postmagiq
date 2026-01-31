"""Authentication routes for user registration, login, and session management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session

from api.auth.jwt import verify_token
from api.auth.providers import get_provider
from api.auth.service import AuthService
from api.services.email_service import email_service
from api.utils.role_flags import get_flags_for_user
from runner.db.engine import get_session_dependency
from runner.db.models import UserRead, UserRole

router = APIRouter(prefix="/v1/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# =============================================================================
# Request/Response Models
# =============================================================================


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# =============================================================================
# Dependencies
# =============================================================================


def get_auth_service(session: Session = Depends(get_session_dependency)) -> AuthService:
    """Dependency to get AuthService with database session."""
    return AuthService(session)


def require_local_auth() -> None:
    """Dependency to require local authentication support.

    Raises 400 if the configured auth provider doesn't support local auth.
    Use this on login, register, and password reset routes.
    """
    provider = get_provider()
    if not provider.supports_local_auth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This endpoint is not available with {provider.name} authentication. "
            f"Please use the {provider.name} login flow instead.",
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """Dependency to get the current authenticated user.

    Validates the access token and returns the user.
    Raises HTTPException 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user_by_id(UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        created_at=user.created_at,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        role=user.role,
        view_as_tier_id=user.view_as_tier_id,
        default_workspace_id=user.default_workspace_id,
    )


# =============================================================================
# Routes
# =============================================================================


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register(
    request: RegisterRequest,
    req: Request,
    _: None = Depends(require_local_auth),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register a new user.

    Creates a new user account and returns access tokens.
    """
    # Get client info for session tracking
    user_agent = req.headers.get("user-agent")
    ip_address = req.client.host if req.client else None

    try:
        user = auth_service.register(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    tokens = auth_service.create_session(
        user_id=user.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    req: Request,
    _: None = Depends(require_local_auth),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate user and return tokens.

    Validates credentials and creates a new session.
    """
    user = auth_service.authenticate(
        email=request.email,
        password=request.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Get client info for session
    user_agent = req.headers.get("user-agent")
    ip_address = req.client.host if req.client else None

    tokens = auth_service.create_session(
        user_id=user.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return TokenResponse(**tokens)


@router.post("/logout", response_model=MessageResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Logout and revoke the current session.

    Requires a valid refresh token to identify the session.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    token_jti = payload.get("jti")
    if token_jti:
        auth_service.revoke_session(token_jti)

    return MessageResponse(message="Successfully logged out")


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: RefreshRequest,
    req: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh access token using a refresh token.

    Validates the refresh token and issues new tokens.
    """
    payload = verify_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    token_jti = payload.get("jti")
    if not token_jti or not auth_service.validate_session(token_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = auth_service.get_user_by_id(UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old session
    auth_service.revoke_session(token_jti)

    # Get client info for new session
    user_agent = req.headers.get("user-agent")
    ip_address = req.client.host if req.client else None

    # Create new session
    tokens = auth_service.create_session(
        user_id=user.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return TokenResponse(**tokens)


@router.get("/me", response_model=UserRead)
def get_me(
    current_user: UserRead = Depends(get_current_user),
) -> UserRead:
    """Get the current authenticated user's profile."""
    return current_user


class FlagsResponse(BaseModel):
    """Response containing feature flags for the current user."""

    show_internal_workflow: bool
    show_image_tools: bool
    show_ai_personas: bool
    show_live_workflow: bool
    show_state_editor: bool
    show_approvals: bool
    show_teams: bool
    show_strategy_admin: bool
    show_costs: bool
    max_circuit_breaker: int


@router.get("/me/flags", response_model=FlagsResponse)
def get_my_flags(
    current_user: UserRead = Depends(get_current_user),
) -> FlagsResponse:
    """Get feature flags for the current authenticated user.

    Returns flags based on the user's role (owner/admin/user).
    """
    flags = get_flags_for_user(current_user)
    return FlagsResponse(**flags)


class ViewAsTierRequest(BaseModel):
    """Request body for setting view-as-tier (owner testing feature)."""

    tier_id: Optional[UUID] = None  # None resets to actual tier


@router.put("/me/view-as-tier", response_model=UserRead)
def set_view_as_tier(
    request: ViewAsTierRequest,
    current_user: UserRead = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """Set the tier to simulate for testing (owner-only).

    Allows owners to view the application as if they were on a different tier.
    This affects usage limits and feature visibility without changing the actual subscription.

    Set tier_id to null to reset to the actual subscription tier.
    """
    if current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can use the view-as-tier feature",
        )

    try:
        user = auth_service.set_view_as_tier(current_user.id, request.tier_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return UserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        created_at=user.created_at,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        role=user.role,
        view_as_tier_id=user.view_as_tier_id,
        default_workspace_id=user.default_workspace_id,
    )


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for reset password."""

    token: str
    password: str = Field(min_length=8, max_length=128)


class UpdateRoleRequest(BaseModel):
    """Request body for updating a user's role."""

    role: UserRole


@router.put("/users/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    current_user: UserRead = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """Update a user's role (owner-only).

    Only users with the 'owner' role can change other users' roles.
    """
    # Only owners can change roles
    if current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can change user roles",
        )

    # Get target user
    target_user = auth_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update role
    target_user.role = request.role
    auth_service.session.add(target_user)
    auth_service.session.commit()
    auth_service.session.refresh(target_user)

    return UserRead(
        id=target_user.id,
        name=target_user.name,
        email=target_user.email,
        created_at=target_user.created_at,
        is_active=target_user.is_active,
        is_superuser=target_user.is_superuser,
        role=target_user.role,
        default_workspace_id=target_user.default_workspace_id,
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    request: ForgotPasswordRequest,
    _: None = Depends(require_local_auth),
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Request a password reset email.

    Always returns success to prevent email enumeration attacks.
    If the email exists, a reset link will be sent.
    """
    user = auth_service.get_user_by_email(request.email)

    if user and user.is_active:
        # Create reset token
        token = auth_service.create_password_reset_token(user.id)

        # Send email (async would be better, but keeping it simple)
        email_service.send_password_reset(user.email, token)

    # Always return success to prevent email enumeration
    return MessageResponse(message="If an account exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: ResetPasswordRequest,
    _: None = Depends(require_local_auth),
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Reset password using a reset token.

    The token is single-use and expires after 1 hour.
    """
    success = auth_service.reset_password(request.token, request.password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return MessageResponse(message="Password has been reset successfully")
