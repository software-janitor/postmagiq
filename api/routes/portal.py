"""Client portal routes for content review and approval.

Provides client-facing endpoints with limited scope:
- GET /portal/login - login page data with workspace branding
- POST /portal/login - client authentication
- GET /portal/posts - list posts for review
- GET /portal/posts/{post_id} - single post detail
- POST /portal/posts/{post_id}/approve - approve a post
- POST /portal/posts/{post_id}/reject - reject a post with feedback
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session

from api.auth.jwt import create_access_token, verify_token
from api.services.portal_service import (
    PortalService,
    PostNotFoundError,
    UnauthorizedError,
    InvalidStateError,
)
from runner.db.engine import get_session_dependency

router = APIRouter(prefix="/portal", tags=["portal"])
security = HTTPBearer(auto_error=False)


# =============================================================================
# Request/Response Models
# =============================================================================


class PortalLoginRequest(BaseModel):
    """Request body for portal login."""

    email: EmailStr
    password: str
    workspace_id: UUID


class PortalLoginResponse(BaseModel):
    """Response for successful portal login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict
    branding: dict


class PortalBrandingResponse(BaseModel):
    """Response for portal branding/login page data."""

    workspace_name: str
    company_name: Optional[str] = None
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    portal_welcome_text: Optional[str] = None
    portal_footer_text: Optional[str] = None
    support_email: Optional[str] = None


class PostListResponse(BaseModel):
    """Response for post list."""

    posts: list[dict]
    total: int


class PostDetailResponse(BaseModel):
    """Response for single post detail."""

    id: str
    post_number: int
    topic: Optional[str] = None
    shape: Optional[str] = None
    cadence: Optional[str] = None
    entry_point: Optional[str] = None
    status: str
    guidance: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    approval_request_id: Optional[str] = None
    approval_status: Optional[str] = None
    decision_notes: Optional[str] = None
    submitted_at: Optional[str] = None


class ApproveRequest(BaseModel):
    """Request body for approving a post."""

    notes: Optional[str] = None


class RejectRequest(BaseModel):
    """Request body for rejecting a post."""

    feedback: str = Field(min_length=1)


class ApprovalResponse(BaseModel):
    """Response for approval/rejection action."""

    success: bool
    post_id: str
    status: str
    message: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# =============================================================================
# Dependencies
# =============================================================================


def get_portal_service() -> PortalService:
    """Dependency to get PortalService."""
    return PortalService()


def get_current_portal_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency to get the current portal user from token.

    Portal tokens have limited scope (viewer-level).
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

    if payload.get("type") != "portal_access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for portal access",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": UUID(payload.get("sub")),
        "workspace_id": UUID(payload.get("workspace_id")),
        "email": payload.get("email"),
        "role": payload.get("role", "viewer"),
    }


# =============================================================================
# Routes
# =============================================================================


@router.get("/login/{workspace_id}", response_model=PortalBrandingResponse)
def get_login_page(
    workspace_id: UUID,
    session: Session = Depends(get_session_dependency),
    portal_service: PortalService = Depends(get_portal_service),
) -> PortalBrandingResponse:
    """Get portal login page data with workspace branding.

    This endpoint is public - no authentication required.
    Returns branding info for the login page.
    """
    branding = portal_service.get_workspace_branding(session, workspace_id)
    if not branding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return PortalBrandingResponse(**branding)


@router.post("/login", response_model=PortalLoginResponse)
def portal_login(
    request: PortalLoginRequest,
    req: Request,
    session: Session = Depends(get_session_dependency),
    portal_service: PortalService = Depends(get_portal_service),
) -> PortalLoginResponse:
    """Authenticate user for portal access.

    Creates a limited-scope token for client portal operations.
    Only grants viewer-level permissions within the specified workspace.
    """
    auth_result = portal_service.authenticate_portal_user(
        session,
        email=request.email,
        password=request.password,
        workspace_id=request.workspace_id,
    )

    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or no access to this workspace",
        )

    # Create portal-specific token with limited scope
    token_data = {
        "sub": auth_result["user_id"],
        "workspace_id": auth_result["workspace_id"],
        "email": auth_result["email"],
        "role": auth_result["role"],
    }
    access_token = create_access_token(token_data, token_type="portal_access")

    # Get branding for response
    branding = portal_service.get_workspace_branding(
        session, request.workspace_id
    )

    return PortalLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,  # 30 minutes
        user={
            "email": auth_result["email"],
            "name": auth_result["name"],
            "role": auth_result["role"],
        },
        branding=branding or {},
    )


@router.get("/posts", response_model=PostListResponse)
def list_posts_for_review(
    status_filter: Optional[str] = None,
    session: Session = Depends(get_session_dependency),
    portal_service: PortalService = Depends(get_portal_service),
    current_user: dict = Depends(get_current_portal_user),
) -> PostListResponse:
    """List posts available for client review.

    Returns posts in review-related statuses (pending_approval, ready, changes_requested).
    """
    workspace_id = current_user["workspace_id"]

    posts = portal_service.get_posts_for_review(
        session, workspace_id, status_filter
    )

    return PostListResponse(posts=posts, total=len(posts))


@router.get("/posts/{post_id}", response_model=PostDetailResponse)
def get_post_detail(
    post_id: UUID,
    session: Session = Depends(get_session_dependency),
    portal_service: PortalService = Depends(get_portal_service),
    current_user: dict = Depends(get_current_portal_user),
) -> PostDetailResponse:
    """Get detailed information about a single post."""
    workspace_id = current_user["workspace_id"]

    post = portal_service.get_post_detail(session, workspace_id, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return PostDetailResponse(**post)


@router.post("/posts/{post_id}/approve", response_model=ApprovalResponse)
def approve_post(
    post_id: UUID,
    request: Optional[ApproveRequest] = None,
    session: Session = Depends(get_session_dependency),
    portal_service: PortalService = Depends(get_portal_service),
    current_user: dict = Depends(get_current_portal_user),
) -> ApprovalResponse:
    """Approve a post for publication.

    Client approves the post, moving it to 'ready' status.
    """
    workspace_id = current_user["workspace_id"]
    user_id = current_user["user_id"]
    notes = request.notes if request else None

    try:
        approval = portal_service.approve_post(
            session, workspace_id, post_id, user_id, notes
        )
        return ApprovalResponse(
            success=True,
            post_id=str(post_id),
            status=approval.status,
            message="Post approved successfully",
        )
    except PostNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except InvalidStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/posts/{post_id}/reject", response_model=ApprovalResponse)
def reject_post(
    post_id: UUID,
    request: RejectRequest,
    session: Session = Depends(get_session_dependency),
    portal_service: PortalService = Depends(get_portal_service),
    current_user: dict = Depends(get_current_portal_user),
) -> ApprovalResponse:
    """Reject a post with feedback.

    Client rejects the post, requiring revisions. Feedback is required.
    """
    workspace_id = current_user["workspace_id"]
    user_id = current_user["user_id"]

    try:
        approval = portal_service.reject_post(
            session, workspace_id, post_id, user_id, request.feedback
        )
        return ApprovalResponse(
            success=True,
            post_id=str(post_id),
            status=approval.status,
            message="Post rejected with feedback",
        )
    except PostNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except InvalidStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
