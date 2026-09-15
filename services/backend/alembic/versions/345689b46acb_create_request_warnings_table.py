"""create request warnings table

Revision ID: 345689b46acb
Revises: 7d8e9f0a1b2c
Create Date: 2026-09-15 10:38:20.885749

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '345689b46acb'
down_revision = '7d8e9f0a1b2c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "request_warnings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("release_id", sa.String(length=512), nullable=True),
        sa.Column(
            "code",
            sa.Enum(
                "mapping_overlap",
                "regrab_indexer_unavailable",
                name="request_warning_code",
            ),
            nullable=False,
        ),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["request_id"], ["media_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["releases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_warnings_request_id", "request_warnings", ["request_id"])
    op.create_index("ix_request_warnings_release_id", "request_warnings", ["release_id"])


def downgrade() -> None:
    op.drop_index("ix_request_warnings_release_id", table_name="request_warnings")
    op.drop_index("ix_request_warnings_request_id", table_name="request_warnings")
    op.drop_table("request_warnings")

    # SQLite has no real enum type; only Postgres needs the type dropped explicitly.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP TYPE request_warning_code"))
