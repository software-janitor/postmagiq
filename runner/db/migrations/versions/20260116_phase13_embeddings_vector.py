"""Phase 13: embeddings vector type and index.

Revision ID: phase13_embeddings_vector
Revises: phase13_market_intel
Create Date: 2026-01-16

Upgrades embeddings.embedding to vector(1536) and adds ivfflat index.
"""

from alembic import op

revision = "phase13_embeddings_vector"
down_revision = "phase13_market_intel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "ALTER TABLE embeddings "
        "ALTER COLUMN embedding TYPE vector(1536) "
        "USING embedding::vector"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_vector "
        "ON embeddings USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vector")
    op.execute(
        "ALTER TABLE embeddings "
        "ALTER COLUMN embedding TYPE double precision[] "
        "USING embedding::double precision[]"
    )
