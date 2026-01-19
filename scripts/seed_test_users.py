#!/usr/bin/env python3
"""Seed test users for development.

Creates test users with different roles for testing the RBAC system.
All users have password: Test123!

Usage:
    python scripts/seed_test_users.py

    Or via make:
    make seed-users
"""

import os
import sys
from datetime import datetime

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set default DATABASE_URL for local development
os.environ.setdefault("DATABASE_URL", "postgresql://orchestrator:orchestrator_dev@localhost:6432/orchestrator")

from uuid import uuid4
from sqlmodel import Session, select
from runner.db.engine import engine, init_db
from runner.db.models import User, Workspace, WorkspaceMembership, WorkspaceRole

# Test accounts (must match Login.tsx)
TEST_USERS = [
    {"email": "owner@test.com", "name": "Test Owner", "role": WorkspaceRole.owner},
    {"email": "admin@test.com", "name": "Test Admin", "role": WorkspaceRole.admin},
    {"email": "editor@test.com", "name": "Test Editor", "role": WorkspaceRole.editor},
    {"email": "viewer@test.com", "name": "Test Viewer", "role": WorkspaceRole.viewer},
]

PASSWORD = "Test123!"


def hash_password(password: str) -> str:
    """Simple password hashing using bcrypt."""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        # Fallback for dev - NOT secure for production
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


def seed_users():
    """Create test users and workspace."""
    print("Initializing database...")
    init_db()

    with Session(engine) as session:
        # Create owner user first (needed for workspace FK)
        owner_data = TEST_USERS[0]  # First user is owner
        owner = session.exec(
            select(User).where(User.email == owner_data["email"])
        ).first()

        if not owner:
            print(f"  Creating owner: {owner_data['email']}")
            owner = User(
                id=uuid4(),
                name=owner_data["name"],
                email=owner_data["email"],
                password_hash=hash_password(PASSWORD),
                is_active=True,
                is_superuser=True,
            )
            session.add(owner)
            session.commit()
            session.refresh(owner)

        # Check if test workspace exists
        workspace = session.exec(
            select(Workspace).where(Workspace.slug == "test-workspace")
        ).first()

        if not workspace:
            print("Creating test workspace...")
            workspace = Workspace(
                id=uuid4(),
                name="Test Workspace",
                slug="test-workspace",
                owner_id=owner.id,
            )
            session.add(workspace)
            session.commit()
            session.refresh(workspace)

        # Create remaining test users (skip owner, already created)
        created_users = [(owner, owner_data["role"])]
        for user_data in TEST_USERS[1:]:  # Skip first (owner)
            existing = session.exec(
                select(User).where(User.email == user_data["email"])
            ).first()

            if existing:
                print(f"  User {user_data['email']} already exists")
                created_users.append((existing, user_data["role"]))
                continue

            print(f"  Creating user: {user_data['email']} ({user_data['role'].value})")
            user = User(
                id=uuid4(),
                name=user_data["name"],
                email=user_data["email"],
                password_hash=hash_password(PASSWORD),
                is_active=True,
                is_superuser=False,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            created_users.append((user, user_data["role"]))

        # Create workspace memberships
        print("\nCreating workspace memberships...")
        for user, role in created_users:
            existing_membership = session.exec(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace.id,
                    WorkspaceMembership.user_id == user.id,
                )
            ).first()

            if existing_membership:
                print(f"  Membership for {user.email} already exists")
                continue

            print(f"  Adding {user.email} as {role.value}")
            membership = WorkspaceMembership(
                id=uuid4(),
                workspace_id=workspace.id,
                user_id=user.id,
                email=user.email,
                role=role,
                invite_status="accepted",
                accepted_at=datetime.utcnow(),
            )
            session.add(membership)

        session.commit()

        print("\n" + "=" * 50)
        print("Test users created successfully!")
        print("=" * 50)
        print(f"\nWorkspace: {workspace.name} (slug: {workspace.slug})")
        print(f"\nTest Accounts (password: {PASSWORD}):")
        for user_data in TEST_USERS:
            print(f"  - {user_data['email']:20} ({user_data['role'].value})")


if __name__ == "__main__":
    seed_users()
