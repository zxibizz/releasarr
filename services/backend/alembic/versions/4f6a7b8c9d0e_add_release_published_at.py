"""Add published_at to releases.

Revision ID: 4f6a7b8c9d0e
Revises: 3e5f6a7b8c9d
Create Date: 2026-09-14 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4f6a7b8c9d0e"
down_revision = "3e5f6a7b8c9d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the nullable indexer publish timestamp column."""

    with op.batch_alter_table("releases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove the `published_at` column."""

    with op.batch_alter_table("releases", schema=None) as batch_op:
        batch_op.drop_column("published_at")
