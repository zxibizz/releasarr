"""add importing media request status

Revision ID: b2c3d4e5f6a7
Revises: a8b9c0d1e2f3
Create Date: 2026-09-16 12:00:01.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a8b9c0d1e2f3'
branch_labels = None
depends_on = None

OLD_STATUSES = ('pending', 'searching', 'downloading', 'monitoring', 'completed', 'failed')
NEW_STATUS = 'importing'


def upgrade() -> None:
    # SQLite stores this enum as plain VARCHAR, so only PostgreSQL's native ENUM
    # type needs the new label.
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(sa.text(f"ALTER TYPE media_request_status ADD VALUE IF NOT EXISTS '{NEW_STATUS}'"))


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    # PostgreSQL cannot remove an ENUM label in place, so the column is parked on
    # ``text`` while the type is recreated without it. Requests left importing
    # fall back to downloading, the state they were promoted from.
    allowed = ", ".join(f"'{label}'" for label in OLD_STATUSES)

    # The column default is stored as ``'pending'::media_request_status`` and
    # keeps depending on the type across the cast to text, so DROP TYPE fails
    # unless it is removed first and restored once the new type exists.
    op.execute(sa.text("ALTER TABLE media_requests ALTER COLUMN status DROP DEFAULT"))
    op.execute(
        sa.text(
            "ALTER TABLE media_requests ALTER COLUMN status TYPE text USING status::text"
        )
    )
    op.execute(
        sa.text(f"UPDATE media_requests SET status = 'downloading' WHERE status = '{NEW_STATUS}'")
    )
    op.execute(sa.text("DROP TYPE media_request_status"))
    op.execute(sa.text(f"CREATE TYPE media_request_status AS ENUM ({allowed})"))
    op.execute(
        sa.text(
            "ALTER TABLE media_requests ALTER COLUMN status TYPE media_request_status "
            "USING status::media_request_status"
        )
    )
    op.execute(sa.text("ALTER TABLE media_requests ALTER COLUMN status SET DEFAULT 'pending'"))
