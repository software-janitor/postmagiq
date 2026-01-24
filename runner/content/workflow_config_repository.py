"""Repository for WorkflowConfig operations.

Handles CRUD and querying for workflow configurations stored in PostgreSQL.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from runner.db.models import (
    WorkflowConfig, WorkflowConfigCreate, WorkflowConfigUpdate,
    WorkflowEnvironment,
)


class WorkflowConfigRepository:
    """Repository for WorkflowConfig operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: WorkflowConfigCreate) -> WorkflowConfig:
        """Create a new workflow configuration."""
        config = WorkflowConfig.model_validate(data)
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def get(self, config_id: UUID) -> Optional[WorkflowConfig]:
        """Get a workflow config by ID."""
        return self.session.get(WorkflowConfig, config_id)

    def get_by_slug(self, slug: str) -> Optional[WorkflowConfig]:
        """Get a workflow config by slug."""
        statement = select(WorkflowConfig).where(WorkflowConfig.slug == slug)
        return self.session.exec(statement).first()

    def get_default(self) -> Optional[WorkflowConfig]:
        """Get the default workflow config (is_default=True and enabled=True)."""
        statement = select(WorkflowConfig).where(
            WorkflowConfig.is_default == True,
            WorkflowConfig.enabled == True,
        )
        return self.session.exec(statement).first()

    def list_all(self) -> list[WorkflowConfig]:
        """List all workflow configs."""
        statement = select(WorkflowConfig).order_by(WorkflowConfig.name)
        return list(self.session.exec(statement).all())

    def list_enabled(self) -> list[WorkflowConfig]:
        """List all enabled workflow configs."""
        statement = (
            select(WorkflowConfig)
            .where(WorkflowConfig.enabled == True)
            .order_by(WorkflowConfig.name)
        )
        return list(self.session.exec(statement).all())

    def list_by_environment(
        self, environment: WorkflowEnvironment
    ) -> list[WorkflowConfig]:
        """List workflow configs for a specific environment."""
        statement = (
            select(WorkflowConfig)
            .where(
                WorkflowConfig.environment == environment,
                WorkflowConfig.enabled == True,
            )
            .order_by(WorkflowConfig.name)
        )
        return list(self.session.exec(statement).all())

    def list_by_tier(self, tier: Optional[str]) -> list[WorkflowConfig]:
        """List workflow configs available for a tier.

        Returns configs where tier_required is None (available to all)
        or matches the specified tier.
        """
        if tier is None:
            # Only configs with no tier requirement
            statement = (
                select(WorkflowConfig)
                .where(
                    WorkflowConfig.tier_required == None,
                    WorkflowConfig.enabled == True,
                )
                .order_by(WorkflowConfig.name)
            )
        else:
            # Configs with no tier requirement OR matching tier
            statement = (
                select(WorkflowConfig)
                .where(
                    WorkflowConfig.enabled == True,
                )
                .where(
                    (WorkflowConfig.tier_required == None) |
                    (WorkflowConfig.tier_required == tier)
                )
                .order_by(WorkflowConfig.name)
            )
        return list(self.session.exec(statement).all())

    def list_for_workspace(
        self,
        environment: WorkflowEnvironment,
        tier: Optional[str] = None,
    ) -> list[WorkflowConfig]:
        """List workflow configs available for a workspace.

        Filters by environment and tier.
        """
        if tier is None:
            statement = (
                select(WorkflowConfig)
                .where(
                    WorkflowConfig.environment == environment,
                    WorkflowConfig.enabled == True,
                    WorkflowConfig.tier_required == None,
                )
                .order_by(WorkflowConfig.name)
            )
        else:
            statement = (
                select(WorkflowConfig)
                .where(
                    WorkflowConfig.environment == environment,
                    WorkflowConfig.enabled == True,
                )
                .where(
                    (WorkflowConfig.tier_required == None) |
                    (WorkflowConfig.tier_required == tier)
                )
                .order_by(WorkflowConfig.name)
            )
        return list(self.session.exec(statement).all())

    def update(
        self, config_id: UUID, data: WorkflowConfigUpdate
    ) -> Optional[WorkflowConfig]:
        """Update a workflow config."""
        config = self.get(config_id)
        if config:
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(config, key, value)
            config.updated_at = datetime.utcnow()
            self.session.add(config)
            self.session.commit()
            self.session.refresh(config)
        return config

    def set_default(self, config_id: UUID) -> Optional[WorkflowConfig]:
        """Set a config as the default (clears is_default on all others)."""
        # Clear current default
        current_default = self.get_default()
        if current_default and current_default.id != config_id:
            current_default.is_default = False
            current_default.updated_at = datetime.utcnow()
            self.session.add(current_default)

        # Set new default
        config = self.get(config_id)
        if config:
            config.is_default = True
            config.updated_at = datetime.utcnow()
            self.session.add(config)
            self.session.commit()
            self.session.refresh(config)
        return config

    def enable(self, config_id: UUID) -> Optional[WorkflowConfig]:
        """Enable a workflow config."""
        config = self.get(config_id)
        if config:
            config.enabled = True
            config.updated_at = datetime.utcnow()
            self.session.add(config)
            self.session.commit()
            self.session.refresh(config)
        return config

    def disable(self, config_id: UUID) -> Optional[WorkflowConfig]:
        """Disable a workflow config."""
        config = self.get(config_id)
        if config:
            config.enabled = False
            config.updated_at = datetime.utcnow()
            self.session.add(config)
            self.session.commit()
            self.session.refresh(config)
        return config

    def delete(self, config_id: UUID) -> bool:
        """Delete a workflow config by ID. Returns True if deleted."""
        config = self.get(config_id)
        if config:
            self.session.delete(config)
            self.session.commit()
            return True
        return False

    def upsert(self, slug: str, data: WorkflowConfigCreate) -> WorkflowConfig:
        """Create or update a workflow config by slug.

        Used by sync_workflows.py to sync from registry.yaml.
        """
        existing = self.get_by_slug(slug)
        if existing:
            # Update existing
            for key, value in data.model_dump().items():
                if key != "slug":  # Don't change slug
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            # Create new
            return self.create(data)
