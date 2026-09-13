"""Add last export timestamp to media_requests.

Revision ID: a7c4e1d95b02
Revises: f3a9d8b1c2e3
Create Date: 2026-09-14 09:30:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7c4e1d95b02"
down_revision = "f3a9d8b1c2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the `exported_at` column."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove the `exported_at` column."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.drop_column("exported_at")
