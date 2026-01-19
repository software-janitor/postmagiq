"""Repository classes for White-label configuration.

These repositories handle white-label operations:
- WhitelabelConfig CRUD and management
- WhitelabelAsset management
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from runner.db.models import (
    WhitelabelConfig, WhitelabelConfigCreate,
    WhitelabelAsset, WhitelabelAssetCreate,
    AssetType, DomainVerificationStatus,
)


# =============================================================================
# WhitelabelConfig Repository
# =============================================================================


class WhitelabelConfigRepository:
    """Repository for WhitelabelConfig operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: WhitelabelConfigCreate) -> WhitelabelConfig:
        """Create a new white-label configuration."""
        config = WhitelabelConfig.model_validate(data)
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def get(self, config_id: UUID) -> Optional[WhitelabelConfig]:
        """Get a white-label configuration by ID."""
        return self.session.get(WhitelabelConfig, config_id)

    def get_by_workspace(self, workspace_id: UUID) -> Optional[WhitelabelConfig]:
        """Get the white-label configuration for a workspace."""
        statement = select(WhitelabelConfig).where(
            WhitelabelConfig.workspace_id == workspace_id
        )
        return self.session.exec(statement).first()

    def get_by_domain(self, domain: str) -> Optional[WhitelabelConfig]:
        """Get a white-label configuration by custom domain.

        Useful for routing requests based on custom domain.
        """
        statement = select(WhitelabelConfig).where(
            WhitelabelConfig.custom_domain == domain,
            WhitelabelConfig.domain_verified == True,
            WhitelabelConfig.is_active == True,
        )
        return self.session.exec(statement).first()

    def list_verified_domains(self) -> list[WhitelabelConfig]:
        """List all verified custom domain configurations."""
        statement = select(WhitelabelConfig).where(
            WhitelabelConfig.domain_verified == True,
            WhitelabelConfig.is_active == True,
        )
        return list(self.session.exec(statement).all())

    def update(self, config_id: UUID, **kwargs) -> Optional[WhitelabelConfig]:
        """Update white-label configuration fields."""
        config = self.get(config_id)
        if config:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            config.updated_at = datetime.utcnow()
            self.session.add(config)
            self.session.commit()
            self.session.refresh(config)
        return config

    def verify_domain(self, config_id: UUID) -> Optional[WhitelabelConfig]:
        """Mark a domain as verified."""
        return self.update(
            config_id,
            domain_verified=True,
            domain_verification_status=DomainVerificationStatus.VERIFIED.value,
            domain_verified_at=datetime.utcnow(),
        )

    def verify_email_domain(self, config_id: UUID) -> Optional[WhitelabelConfig]:
        """Mark an email domain as verified."""
        return self.update(config_id, email_domain_verified=True)

    def deactivate(self, config_id: UUID) -> Optional[WhitelabelConfig]:
        """Deactivate a white-label configuration."""
        return self.update(config_id, is_active=False)

    def activate(self, config_id: UUID) -> Optional[WhitelabelConfig]:
        """Activate a white-label configuration."""
        return self.update(config_id, is_active=True)

    def delete(self, config_id: UUID) -> bool:
        """Delete a white-label configuration by ID. Returns True if deleted."""
        config = self.get(config_id)
        if config:
            self.session.delete(config)
            self.session.commit()
            return True
        return False


# =============================================================================
# WhitelabelAsset Repository
# =============================================================================


class WhitelabelAssetRepository:
    """Repository for WhitelabelAsset operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: WhitelabelAssetCreate) -> WhitelabelAsset:
        """Create a new white-label asset."""
        asset = WhitelabelAsset.model_validate(data)
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def get(self, asset_id: UUID) -> Optional[WhitelabelAsset]:
        """Get an asset by ID."""
        return self.session.get(WhitelabelAsset, asset_id)

    def get_by_workspace_and_type(
        self, workspace_id: UUID, asset_type: AssetType
    ) -> Optional[WhitelabelAsset]:
        """Get an asset by workspace and type.

        Returns the most recently uploaded asset of the given type.
        """
        statement = (
            select(WhitelabelAsset)
            .where(
                WhitelabelAsset.workspace_id == workspace_id,
                WhitelabelAsset.asset_type == asset_type.value,
            )
            .order_by(WhitelabelAsset.uploaded_at.desc())
        )
        return self.session.exec(statement).first()

    def list_by_workspace(self, workspace_id: UUID) -> list[WhitelabelAsset]:
        """List all assets for a workspace."""
        statement = select(WhitelabelAsset).where(
            WhitelabelAsset.workspace_id == workspace_id
        )
        return list(self.session.exec(statement).all())

    def list_by_type(
        self, workspace_id: UUID, asset_type: AssetType
    ) -> list[WhitelabelAsset]:
        """List all assets of a specific type for a workspace."""
        statement = select(WhitelabelAsset).where(
            WhitelabelAsset.workspace_id == workspace_id,
            WhitelabelAsset.asset_type == asset_type.value,
        )
        return list(self.session.exec(statement).all())

    def delete(self, asset_id: UUID) -> bool:
        """Delete an asset by ID. Returns True if deleted."""
        asset = self.get(asset_id)
        if asset:
            self.session.delete(asset)
            self.session.commit()
            return True
        return False

    def delete_by_workspace_and_type(
        self, workspace_id: UUID, asset_type: AssetType
    ) -> int:
        """Delete all assets of a specific type for a workspace.

        Returns the number of assets deleted.
        """
        assets = self.list_by_type(workspace_id, asset_type)
        count = len(assets)
        for asset in assets:
            self.session.delete(asset)
        if count > 0:
            self.session.commit()
        return count
