"""Add info_url to releases.

Revision ID: 3e5f6a7b8c9d
Revises: 2d3e4f5a6b7c
Create Date: 2026-09-14 11:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3e5f6a7b8c9d"
down_revision = "2d3e4f5a6b7c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the nullable tracker page URL column."""

    with op.batch_alter_table("releases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("info_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    """Remove the `info_url` column."""

    with op.batch_alter_table("releases", schema=None) as batch_op:
        batch_op.drop_column("info_url")
