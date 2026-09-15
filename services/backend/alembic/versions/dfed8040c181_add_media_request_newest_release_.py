"""add media request newest release published at

Revision ID: dfed8040c181
Revises: b8f1a2c3d4e5
Create Date: 2026-09-15 15:00:55.882517

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dfed8040c181'
down_revision = 'b8f1a2c3d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add `newest_release_published_at`, backfilled from existing releases."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("newest_release_published_at", sa.DateTime(timezone=True), nullable=True)
        )

    # Was previously derived at read time from the linked releases; now stored so
    # the state recompute use case can write it back like any other column.
    op.execute(
        sa.text(
            """
            UPDATE media_requests
            SET newest_release_published_at = (
                SELECT MAX(releases.published_at)
                FROM release_request_links
                JOIN releases ON releases.id = release_request_links.release_id
                WHERE release_request_links.request_id = media_requests.id
            )
            """
        )
    )


def downgrade() -> None:
    """Drop the newest_release_published_at column."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.drop_column("newest_release_published_at")
