"""Add the indexer search query to releases.

Revision ID: 7a1f5c2e9d43
Revises: d4b8c1f60a72
Create Date: 2026-09-16 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1f5c2e9d43"
down_revision = "d4b8c1f60a72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the nullable query column.

    Left NULL for rows grabbed before it existed and for hand-supplied
    releases: neither has a query to replay, and the re-grab check falls back to
    the release name for the former. Text() rather than a bounded string because
    a query a user typed is not ours to truncate - the same reason `name` is.
    """

    with op.batch_alter_table("releases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("search_query", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove the `search_query` column."""

    with op.batch_alter_table("releases", schema=None) as batch_op:
        batch_op.drop_column("search_query")
