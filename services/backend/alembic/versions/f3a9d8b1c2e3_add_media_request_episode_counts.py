"""Add episode count columns to media_requests.

Revision ID: f3a9d8b1c2e3
Revises: e1f36b8ac704
Create Date: 2026-09-13 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3a9d8b1c2e3"
down_revision = "e1f36b8ac704"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add `aired_episodes` and `downloaded_episodes` columns."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("aired_episodes", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("downloaded_episodes", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove the episode count columns."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.drop_column("downloaded_episodes")
        batch_op.drop_column("aired_episodes")
