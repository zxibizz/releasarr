"""Simplify service_api_keys to a single, user-independent admin key.

Service keys are no longer bound to a user, named, or individually revocable:
there is exactly one, it always authenticates as an admin, and it is replaced
(not soft-revoked) when rotated.

Revision ID: 6c7d8e9f0a1b
Revises: 5b6c7d8e9f0a
Create Date: 2026-09-14 13:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6c7d8e9f0a1b"
down_revision = "5b6c7d8e9f0a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only one key may exist going forward; keep the most recently created row, if any.
    op.execute(
        "DELETE FROM service_api_keys WHERE id NOT IN ("
        "SELECT id FROM ("
        "SELECT id FROM service_api_keys ORDER BY created_at DESC LIMIT 1"
        ") AS keep)"
    )
    # recreate=always: user_id carries a FK, which SQLite refuses to drop in place.
    with op.batch_alter_table("service_api_keys", schema=None, recreate="always") as batch_op:
        batch_op.drop_index("ix_service_api_keys_user_id")
        batch_op.drop_column("user_id")
        batch_op.drop_column("name")
        batch_op.drop_column("is_active")
        batch_op.drop_column("expires_at")


def downgrade() -> None:
    with op.batch_alter_table("service_api_keys", schema=None, recreate="always") as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=64), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("user_id", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False)
        )
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_service_api_keys_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_service_api_keys_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
