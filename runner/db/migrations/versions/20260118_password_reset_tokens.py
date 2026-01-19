"""Add password_reset_tokens table.

Revision ID: 20260118_password_reset
Revises: 009_user_role
Create Date: 2026-01-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '20260118_password_reset'
down_revision: Union[str, None] = '009_user_role'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create password_reset_tokens table."""
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_password_reset_tokens_user_id'),
        'password_reset_tokens',
        ['user_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_password_reset_tokens_token'),
        'password_reset_tokens',
        ['token'],
        unique=True
    )


def downgrade() -> None:
    """Drop password_reset_tokens table."""
    op.drop_index(op.f('ix_password_reset_tokens_token'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
