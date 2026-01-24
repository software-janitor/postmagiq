#!/usr/bin/env python3
"""Sync workflow configurations from registry.yaml to database.

Reads workflows/registry.yaml and upserts workflow configs to the
workflow_configs table, filtering by deployment environment.

Usage:
    python scripts/sync_workflows.py

    Or via make:
    make sync-workflows

Environment:
    DEPLOYMENT_ENV: production, development, or staging (default: development)
"""

import os
import sys
from pathlib import Path

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set default DATABASE_URL for local development
os.environ.setdefault("DATABASE_URL", "postgresql://orchestrator:orchestrator_dev@localhost:6432/orchestrator")

import yaml
from uuid import uuid4
from sqlmodel import Session, select
from runner.db.engine import engine, init_db
from runner.db.models import WorkflowConfig, WorkflowEnvironment


# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
REGISTRY_PATH = PROJECT_ROOT / "workflows" / "registry.yaml"
DEPLOYMENT_ENV = os.environ.get("DEPLOYMENT_ENV", "development")


def load_registry() -> dict:
    """Load workflows/registry.yaml."""
    if not REGISTRY_PATH.exists():
        print(f"Error: Registry not found at {REGISTRY_PATH}")
        sys.exit(1)

    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f)


def get_allowed_environments(deployment_env: str) -> list[str]:
    """Get allowed workflow environments for a deployment.

    Based on deployment.include_environments from registry.yaml.
    """
    registry = load_registry()
    deployment = registry.get("deployment", {}).get(deployment_env, {})
    return deployment.get("include_environments", [deployment_env])


def sync_workflows():
    """Sync workflow configs from registry to database."""
    init_db()

    registry = load_registry()
    workflows = registry.get("workflows", {})
    allowed_envs = get_allowed_environments(DEPLOYMENT_ENV)

    print(f"Deployment environment: {DEPLOYMENT_ENV}")
    print(f"Allowed workflow environments: {allowed_envs}")
    print()

    with Session(engine) as session:
        created = 0
        updated = 0
        skipped = 0
        disabled = 0

        for slug, meta in workflows.items():
            workflow_env = meta.get("environment", "production")

            # Check if this workflow is allowed in current deployment
            if workflow_env not in allowed_envs:
                print(f"  Skipped: {slug} (environment {workflow_env} not in {allowed_envs})")
                skipped += 1
                continue

            # Check if workflow already exists
            existing = session.exec(
                select(WorkflowConfig).where(WorkflowConfig.slug == slug)
            ).first()

            # Prepare workflow data
            config_data = {
                "name": meta.get("name", slug),
                "slug": slug,
                "description": meta.get("description"),
                "config_file": meta.get("config_file", f"configs/{slug}.yaml"),
                "environment": WorkflowEnvironment(workflow_env),
                "features": meta.get("features"),
                "tier_required": meta.get("tier_required"),
                "enabled": meta.get("enabled", True),
            }

            if existing:
                # Update existing workflow
                changed = False
                for key, value in config_data.items():
                    if getattr(existing, key) != value:
                        setattr(existing, key, value)
                        changed = True

                if changed:
                    session.add(existing)
                    updated += 1
                    status = "enabled" if config_data["enabled"] else "disabled"
                    print(f"  Updated: {slug} ({status})")
                else:
                    skipped += 1
                    print(f"  Skipped: {slug} (no changes)")
            else:
                # Create new workflow
                workflow = WorkflowConfig(
                    id=uuid4(),
                    **config_data,
                )
                session.add(workflow)
                created += 1
                status = "enabled" if config_data["enabled"] else "disabled"
                print(f"  Created: {slug} ({status})")

            if not config_data["enabled"]:
                disabled += 1

        # Disable workflows not in registry (orphaned)
        all_slugs = set(workflows.keys())
        orphaned = session.exec(
            select(WorkflowConfig).where(
                WorkflowConfig.slug.notin_(all_slugs),
                WorkflowConfig.enabled == True,
            )
        ).all()

        for orphan in orphaned:
            orphan.enabled = False
            session.add(orphan)
            print(f"  Disabled: {orphan.slug} (not in registry)")
            disabled += 1

        session.commit()

        print()
        print(f"Summary: {created} created, {updated} updated, {skipped} unchanged, {disabled} disabled")


if __name__ == "__main__":
    print("Syncing workflow configurations...")
    print()
    sync_workflows()
    print()
    print("Done!")
