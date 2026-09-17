"""Add indexes backing the request list filters.

The full-library sync makes the requests table grow from user-driven requests to
the whole monitored library, so the list endpoint's status filter and title
search/sort need an index each.

Revision ID: c5a8d3f19e02
Revises: a1b2c3d4e5f6
Create Date: 2026-09-17 00:00:00.000000

"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "c5a8d3f19e02"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_media_requests_status_created_at",
        "media_requests",
        ["status", "created_at"],
    )
    op.create_index("ix_media_requests_title", "media_requests", ["title"])


def downgrade() -> None:
    op.drop_index("ix_media_requests_title", table_name="media_requests")
    op.drop_index("ix_media_requests_status_created_at", table_name="media_requests")
