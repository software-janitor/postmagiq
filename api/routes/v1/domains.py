"""Custom domain routes for white-label workspaces.

Provides endpoints for:
- Domain verification (TXT record setup)
- DKIM key generation and verification
- Custom domain status and management
"""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceContext,
    require_workspace_scope,
)
from api.services.domain_service import (
    DomainService,
    DomainNotFoundError,
    DomainAlreadyVerifiedError,
    DomainVerificationFailedError,
    DKIMGenerationError,
)
from runner.db.engine import get_session_dependency


router = APIRouter(prefix="/v1/w/{workspace_id}/domains", tags=["domains"])

domain_service = DomainService()


# =============================================================================
# Request/Response Models
# =============================================================================


class InitiateDomainVerificationRequest(BaseModel):
    """Request to initiate domain verification."""

    custom_domain: str = Field(
        min_length=3,
        max_length=255,
        description="The custom domain to verify (e.g., content.agency.com)",
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9.-]+[a-zA-Z0-9]$",
    )


class DomainVerificationResponse(BaseModel):
    """Response with domain verification instructions."""

    custom_domain: str
    verification_token: str
    dns_instructions: dict
    message: str


class DomainStatusResponse(BaseModel):
    """Response with current domain verification status."""

    configured: bool
    custom_domain: Optional[str]
    verified: bool
    status: Optional[str]
    verified_at: Optional[datetime]
    verification_token: Optional[str]
    instructions: Optional[dict]


class DomainVerificationResultResponse(BaseModel):
    """Response after domain verification attempt."""

    verified: bool
    custom_domain: str
    verified_at: Optional[datetime]
    message: str


class InitiateDKIMRequest(BaseModel):
    """Request to generate DKIM keys."""

    email_domain: str = Field(
        min_length=3,
        max_length=255,
        description="The email domain (e.g., mail.agency.com)",
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9.-]+[a-zA-Z0-9]$",
    )


class DKIMResponse(BaseModel):
    """Response with DKIM setup information."""

    selector: str
    email_domain: str
    dns_record_name: str
    dns_record_value: str
    private_key: str  # Only returned once at generation
    instructions: dict


class DKIMStatusResponse(BaseModel):
    """Response with current DKIM status."""

    configured: bool
    email_domain: Optional[str]
    selector: Optional[str]
    verified: bool
    instructions: Optional[dict]


class DKIMVerificationResultResponse(BaseModel):
    """Response after DKIM verification attempt."""

    verified: bool
    email_domain: str
    message: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# =============================================================================
# Domain Verification Routes
# =============================================================================


@router.post(
    "/verify",
    response_model=DomainVerificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def initiate_domain_verification(
    request: InitiateDomainVerificationRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKSPACE_SETTINGS))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Initiate domain verification by generating a verification token.

    Returns DNS record instructions. Add the TXT record to your DNS,
    then call GET /domains/status to check, or POST /domains/verify to verify.

    Requires workspace:settings scope (admin or owner).
    """
    try:
        token = domain_service.generate_verification_token(
            session,
            ctx.workspace_id,
            request.custom_domain,
        )
    except DomainAlreadyVerifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    txt_record_name = f"_quillexir-verify.{request.custom_domain}"

    return DomainVerificationResponse(
        custom_domain=request.custom_domain,
        verification_token=token,
        dns_instructions={
            "txt_record": {
                "type": "TXT",
                "name": txt_record_name,
                "value": token,
            },
            "cname_record": {
                "type": "CNAME",
                "name": request.custom_domain,
                "value": "app.quillexir.com",
            },
        },
        message="Add the DNS records, then verify at POST /domains/verify",
    )


@router.get("/status", response_model=DomainStatusResponse)
async def get_domain_status(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKSPACE_SETTINGS))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get the current domain verification status.

    Returns configured domain, verification status, and DNS instructions if pending.

    Requires workspace:settings scope (admin or owner).
    """
    status_info = domain_service.get_verification_status(session, ctx.workspace_id)
    return DomainStatusResponse(**status_info)


@router.post("/verify/check", response_model=DomainVerificationResultResponse)
async def verify_domain(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKSPACE_SETTINGS))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Verify the domain by checking DNS TXT record.

    Call this after adding the DNS records to verify ownership.

    Requires workspace:settings scope (admin or owner).
    """
    try:
        domain_service.verify_domain(session, ctx.workspace_id)
    except DomainNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except DomainVerificationFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Get updated status
    status_info = domain_service.get_verification_status(session, ctx.workspace_id)

    return DomainVerificationResultResponse(
        verified=True,
        custom_domain=status_info["custom_domain"],
        verified_at=status_info["verified_at"],
        message="Domain verified successfully",
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def remove_custom_domain(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKSPACE_SETTINGS))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Remove the custom domain from the workspace.

    This will disassociate the domain but DNS records can remain in place.

    Requires workspace:settings scope (admin or owner).
    """
    removed = domain_service.remove_custom_domain(session, ctx.workspace_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom domain configured",
        )


# =============================================================================
# DKIM Routes
# =============================================================================


@router.post("/dkim", response_model=DKIMResponse, status_code=status.HTTP_201_CREATED)
async def generate_dkim_keys(
    request: InitiateDKIMRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKSPACE_SETTINGS))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Generate DKIM keypair for email authentication.

    Returns the private key once - store it securely.
    Add the provided DNS TXT record to enable DKIM signing.

    Requires workspace:settings scope (admin or owner).
    """
    try:
        result = domain_service.generate_dkim_keypair(
            session,
            ctx.workspace_id,
            request.email_domain,
        )
    except DKIMGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return DKIMResponse(
        selector=result["selector"],
        email_domain=result["email_domain"],
        dns_record_name=result["dns_record_name"],
        dns_record_value=result["dns_record_value"],
        private_key=result["private_key"],
        instructions=result["instructions"],
    )


@router.get("/dkim/status", response_model=DKIMStatusResponse)
async def get_dkim_status(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKSPACE_SETTINGS))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get the current DKIM configuration status.

    Returns email domain, selector, verification status, and DNS instructions.

    Requires workspace:settings scope (admin or owner).
    """
    status_info = domain_service.get_dkim_status(session, ctx.workspace_id)
    return DKIMStatusResponse(**status_info)


@router.post("/dkim/verify", response_model=DKIMVerificationResultResponse)
async def verify_dkim_setup(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.WORKSPACE_SETTINGS))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Verify the DKIM DNS record is properly configured.

    Call this after adding the DKIM DNS record.

    Requires workspace:settings scope (admin or owner).
    """
    try:
        domain_service.verify_dkim_setup(session, ctx.workspace_id)
    except DomainNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except DomainVerificationFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Get updated status
    status_info = domain_service.get_dkim_status(session, ctx.workspace_id)

    return DKIMVerificationResultResponse(
        verified=True,
        email_domain=status_info["email_domain"],
        message="DKIM DNS record verified successfully",
    )
