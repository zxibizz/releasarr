"""Add owner_user_id to media_requests.

Revision ID: 2d3e4f5a6b7c
Revises: 1c2d3e4f5a6b
Create Date: 2026-09-14 10:05:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2d3e4f5a6b7c"
down_revision = "1c2d3e4f5a6b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the nullable owner FK. Null means the request has no owning user."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_user_id", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_media_requests_owner_user_id", ["owner_user_id"])
        batch_op.create_foreign_key(
            "fk_media_requests_owner_user_id",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Drop the owner FK."""

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.drop_constraint("fk_media_requests_owner_user_id", type_="foreignkey")
        batch_op.drop_index("ix_media_requests_owner_user_id")
        batch_op.drop_column("owner_user_id")
