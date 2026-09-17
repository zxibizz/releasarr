"""Create the app_settings override table.

Revision ID: a1b2c3d4e5f6
Revises: c3d4e5f6a7b8
Create Date: 2026-09-17 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the singleton runtime-settings override row.

    Stores only the fields the environment does not pin. ``revision`` is bumped
    on every write so the API and scheduler processes notice a change without a
    restart.
    """

    op.create_table(
        "app_settings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("overrides", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
