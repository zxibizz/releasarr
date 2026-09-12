"""Add Sonarr linkage columns to media requests.

Revision ID: 2f6a6434600c
Revises: c2412e7b4945
Create Date: 2025-09-27 14:19:21.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2f6a6434600c"
down_revision = "c2412e7b4945"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add `sonarr_series_id` column and related constraint."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sonarr_series_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_media_requests_sonarr_series_id",
            ["sonarr_series_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_media_requests_sonarr_series_season",
            ["sonarr_series_id", "season_number"],
        )


def downgrade() -> None:
    """Remove Sonarr linkage fields."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_media_requests_sonarr_series_season",
            type_="unique",
        )
        batch_op.drop_index("ix_media_requests_sonarr_series_id")
        batch_op.drop_column("sonarr_series_id")

