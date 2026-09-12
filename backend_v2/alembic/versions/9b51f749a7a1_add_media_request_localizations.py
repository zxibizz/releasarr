"""Add localized metadata storage to media requests.

Revision ID: 9b51f749a7a1
Revises: 2f6a6434600c
Create Date: 2025-02-08 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b51f749a7a1"
down_revision = "2f6a6434600c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the `localizations` JSON column to `media_requests`."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "localizations",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )

    # Ensure existing rows receive an empty object before dropping the default.
    op.execute("UPDATE media_requests SET localizations = '{}' WHERE localizations IS NULL")

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.alter_column("localizations", server_default=None)


def downgrade() -> None:
    """Remove the `localizations` column."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.drop_column("localizations")

