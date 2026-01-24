"""Add user role column for feature flags.

Revision ID: 009_user_role
Revises: 009_voice_profiles_modular
Create Date: 2026-01-17

Adds:
- role column to users table (enum: owner/admin/user)
- Default value: 'user' for simplified experience
- Sets the first user (by created_at) as 'owner'
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_user_role'
down_revision = '009_voice_profiles_modular'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for user roles
    op.execute("CREATE TYPE userrole AS ENUM ('owner', 'admin', 'user')")

    # Add role column to users table with default 'user'
    op.add_column(
        'users',
        sa.Column(
            'role',
            sa.Enum('owner', 'admin', 'user', name='userrole'),
            nullable=False,
            server_default='user'
        )
    )

    # Set the first user (by created_at) as owner
    # This ensures existing data has an owner after migration
    op.execute("""
        UPDATE users
        SET role = 'owner'
        WHERE id = (
            SELECT id FROM users
            ORDER BY created_at ASC
            LIMIT 1
        )
    """)


def downgrade() -> None:
    op.drop_column('users', 'role')
    op.execute("DROP TYPE userrole")
