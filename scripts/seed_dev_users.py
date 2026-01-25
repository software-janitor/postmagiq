#!/usr/bin/env python3
"""Seed development users via the AuthService.

This script creates test users for development using the same code paths
as production registration, ensuring proper workspace and subscription setup.

Usage:
    python scripts/seed_dev_users.py
    # or via make:
    make db-seed
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.auth.service import AuthService
from runner.db.engine import get_session


DEV_USERS = [
    {
        "email": "owner@example.com",
        "password": "password123",
        "full_name": "Dev Owner",
    },
]


def seed_dev_users():
    """Seed development users using AuthService."""
    with get_session() as session:
        auth_service = AuthService(session)

        for user_data in DEV_USERS:
            try:
                # Check if user exists
                existing = auth_service.get_user_by_email(user_data["email"])
                if existing:
                    print(f"User {user_data['email']} already exists, skipping")
                    continue

                # Register user (creates user, workspace, membership, subscription)
                user = auth_service.register(
                    email=user_data["email"],
                    password=user_data["password"],
                    full_name=user_data["full_name"],
                )
                print(f"Created user: {user.email} (id: {user.id})")

            except ValueError as e:
                print(f"Skipped {user_data['email']}: {e}")
            except Exception as e:
                print(f"Error creating {user_data['email']}: {e}")
                raise


if __name__ == "__main__":
    seed_dev_users()
    print("Done seeding dev users")
