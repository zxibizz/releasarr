"""Add the regrab sweep's check timestamp to releases.

Revision ID: c81d4a7f2b90
Revises: e7b4c9d2a138
Create Date: 2026-09-20 12:20:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c81d4a7f2b90"
down_revision = "e7b4c9d2a138"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the nullable regrab check timestamp column."""

    with op.batch_alter_table("releases", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("regrab_checked_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    """Remove the `regrab_checked_at` column."""

    with op.batch_alter_table("releases", schema=None) as batch_op:
        batch_op.drop_column("regrab_checked_at")
