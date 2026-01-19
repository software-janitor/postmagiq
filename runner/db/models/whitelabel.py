"""White-label configuration models for Phase 10.

Includes:
- WhitelabelConfig: workspace branding, custom domain, email settings
- WhitelabelAsset: uploaded assets (logo, favicon, banner)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# Enums
# =============================================================================


class AssetType(str, Enum):
    """Types of white-label assets."""
    LOGO = "logo"
    FAVICON = "favicon"
    BANNER = "banner"


class DomainVerificationStatus(str, Enum):
    """Status of domain verification."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


# =============================================================================
# WhitelabelConfig
# =============================================================================


class WhitelabelConfigBase(SQLModel):
    """Base fields for white-label configuration."""

    # Custom domain settings
    custom_domain: Optional[str] = Field(default=None, index=True)
    domain_verified: bool = Field(default=False)
    domain_verification_token: Optional[str] = None
    domain_verification_status: str = Field(
        default=DomainVerificationStatus.PENDING.value
    )
    domain_verified_at: Optional[datetime] = None

    # Branding
    company_name: Optional[str] = None
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None  # For dark mode
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None  # Hex color, e.g., "#1a73e8"
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None

    # Portal settings
    portal_welcome_text: Optional[str] = None
    portal_footer_text: Optional[str] = None
    support_email: Optional[str] = None

    # Email settings
    email_domain: Optional[str] = Field(default=None, max_length=255)
    email_from_name: Optional[str] = Field(default=None, max_length=255)
    email_reply_to: Optional[str] = Field(default=None, max_length=255)
    email_domain_verified: bool = Field(default=False)
    dkim_selector: Optional[str] = Field(default=None, max_length=50)
    dkim_public_key: Optional[str] = None
    dkim_private_key_ref: Optional[str] = None  # Reference to secret storage

    # Status
    is_active: bool = Field(default=True)


class WhitelabelConfig(UUIDModel, WhitelabelConfigBase, TimestampMixin, table=True):
    """White-label configuration for a workspace.

    Enables workspaces to customize branding, use custom domains,
    and configure custom email settings.
    """

    __tablename__ = "whitelabel_configs"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True, unique=True)

    @staticmethod
    def generate_verification_token() -> str:
        """Generate a random domain verification token.

        Returns:
            str: A secure random token prefixed with 'postmatiq-verify-'
        """
        import secrets
        return f"postmatiq-verify-{secrets.token_urlsafe(32)}"

    @staticmethod
    def generate_dkim_selector() -> str:
        """Generate a DKIM selector name.

        Returns:
            str: A unique DKIM selector name
        """
        import secrets
        return f"pm{secrets.token_hex(4)}"


class WhitelabelConfigCreate(WhitelabelConfigBase):
    """Schema for creating a white-label configuration."""

    workspace_id: UUID


class WhitelabelConfigRead(WhitelabelConfigBase):
    """Schema for reading a white-label configuration."""

    id: UUID
    workspace_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]


# =============================================================================
# WhitelabelAsset
# =============================================================================


class WhitelabelAssetBase(SQLModel):
    """Base fields for white-label assets."""

    asset_type: str  # AssetType value
    file_path: str


class WhitelabelAsset(UUIDModel, WhitelabelAssetBase, table=True):
    """Uploaded white-label assets for a workspace.

    Stores references to uploaded files like logos, favicons, and banners.
    """

    __tablename__ = "whitelabel_assets"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class WhitelabelAssetCreate(WhitelabelAssetBase):
    """Schema for creating a white-label asset."""

    workspace_id: UUID


class WhitelabelAssetRead(WhitelabelAssetBase):
    """Schema for reading a white-label asset."""

    id: UUID
    workspace_id: UUID
    uploaded_at: datetime
