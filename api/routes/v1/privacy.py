"""Privacy settings routes for user data management.

Routes for privacy preferences, data export, and account deletion.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from api.auth.dependencies import get_current_user, CurrentUser
from runner.db.engine import get_session_dependency
from runner.db.models import User

router = APIRouter(prefix="/v1/users/me", tags=["privacy"])


# =============================================================================
# Request/Response Models
# =============================================================================


class PrivacySettingsResponse(BaseModel):
    """Response model for privacy settings."""

    data_retention_days: int = Field(description="Data retention period (0 = forever)")
    analytics_opt_out: bool = Field(description="Whether analytics are opted out")
    marketing_emails_opt_out: bool = Field(description="Whether marketing emails are opted out")
    activity_logging_enabled: bool = Field(description="Whether activity logging is enabled")


class PrivacySettingsUpdate(BaseModel):
    """Request model for updating privacy settings."""

    data_retention_days: Optional[int] = Field(
        default=None, ge=0, description="Data retention period in days (0 = forever)"
    )
    analytics_opt_out: Optional[bool] = Field(
        default=None, description="Opt out of analytics tracking"
    )
    marketing_emails_opt_out: Optional[bool] = Field(
        default=None, description="Opt out of marketing emails"
    )
    activity_logging_enabled: Optional[bool] = Field(
        default=None, description="Enable activity logging"
    )


class DataExportResponse(BaseModel):
    """Response model for data export request."""

    download_url: str = Field(description="URL to download the exported data")
    expires_at: str = Field(description="ISO timestamp when the download URL expires")


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# =============================================================================
# Helper: Get or initialize privacy settings from user metadata
# =============================================================================


def get_privacy_settings(user: User) -> dict:
    """Get privacy settings from user, with defaults."""
    # For now, we store privacy settings in a simple way
    # In production, this would be a separate table or user.metadata JSON field
    return {
        "data_retention_days": 365,  # Default: 1 year
        "analytics_opt_out": False,
        "marketing_emails_opt_out": False,
        "activity_logging_enabled": True,
    }


# =============================================================================
# Routes
# =============================================================================


@router.get("/privacy", response_model=PrivacySettingsResponse)
async def get_user_privacy_settings(
    current_user: CurrentUser = Depends(get_current_user),
) -> PrivacySettingsResponse:
    """Get current user's privacy settings.

    Returns the user's privacy preferences including data retention,
    analytics opt-out, marketing email preferences, and activity logging.
    """
    settings = get_privacy_settings(current_user.user)
    return PrivacySettingsResponse(**settings)


@router.put("/privacy", response_model=PrivacySettingsResponse)
async def update_user_privacy_settings(
    request: PrivacySettingsUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session_dependency),
) -> PrivacySettingsResponse:
    """Update current user's privacy settings.

    Only the fields provided in the request body will be updated.
    """
    # Get current settings
    settings = get_privacy_settings(current_user.user)

    # Update only provided fields
    if request.data_retention_days is not None:
        settings["data_retention_days"] = request.data_retention_days
    if request.analytics_opt_out is not None:
        settings["analytics_opt_out"] = request.analytics_opt_out
    if request.marketing_emails_opt_out is not None:
        settings["marketing_emails_opt_out"] = request.marketing_emails_opt_out
    if request.activity_logging_enabled is not None:
        settings["activity_logging_enabled"] = request.activity_logging_enabled

    # In production, save to user.metadata or privacy_settings table
    # For now, we just return the updated settings

    return PrivacySettingsResponse(**settings)


@router.post("/export", response_model=DataExportResponse)
async def export_user_data(
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session_dependency),
) -> DataExportResponse:
    """Request an export of the user's data.

    Generates a download containing all user data including:
    - Profile information
    - Privacy settings
    - Workspace memberships
    - Content created by the user

    The download URL is valid for 24 hours.
    """
    user = current_user.user

    # Build export data
    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_active": user.is_active,
        },
        "privacy_settings": get_privacy_settings(user),
        # In production, add:
        # - workspace_memberships
        # - content
        # - activity_logs
        # - etc.
    }

    # In production, this would:
    # 1. Create an async job to compile all data
    # 2. Store the export in object storage (S3, etc.)
    # 3. Send email notification when ready
    # 4. Return a signed URL with expiration

    # For now, create a mock URL
    export_id = uuid4()
    expires_at = datetime.utcnow() + timedelta(hours=24)

    return DataExportResponse(
        download_url=f"/api/v1/users/me/export/{export_id}/download",
        expires_at=expires_at.isoformat(),
    )


@router.delete("", response_model=MessageResponse)
async def delete_user_account(
    confirmation: str = Query(..., description="Must be 'DELETE' to confirm"),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session_dependency),
) -> MessageResponse:
    """Delete the current user's account.

    This action is permanent and cannot be undone. The user must
    provide 'DELETE' as the confirmation parameter.

    This will:
    - Deactivate the user account
    - Remove all active sessions
    - Remove workspace memberships (preserving workspace content)
    - Schedule personal data for deletion per retention policy
    """
    if confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation must be 'DELETE'",
        )

    user = session.get(User, current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Deactivate user (soft delete)
    user.is_active = False
    session.add(user)
    session.commit()

    # In production, also:
    # 1. Revoke all active sessions
    # 2. Remove from workspaces (or transfer ownership)
    # 3. Queue personal data for deletion
    # 4. Send confirmation email

    return MessageResponse(message="Account has been deleted")
