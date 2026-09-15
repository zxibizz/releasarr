"""add monitoring media request status

Revision ID: b8f1a2c3d4e5
Revises: 345689b46acb
Create Date: 2026-09-15 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b8f1a2c3d4e5'
down_revision = '345689b46acb'
branch_labels = None
depends_on = None

OLD_STATUSES = ('pending', 'searching', 'downloading', 'completed', 'failed')
NEW_STATUS = 'monitoring'


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
    # ``text`` while the type is recreated without it. Requests left monitoring
    # fall back to pending, the status the release sync promotes them from.
    allowed = ", ".join(f"'{label}'" for label in OLD_STATUSES)

    op.execute(
        sa.text(
            "ALTER TABLE media_requests ALTER COLUMN status TYPE text USING status::text"
        )
    )
    op.execute(
        sa.text(f"UPDATE media_requests SET status = 'pending' WHERE status = '{NEW_STATUS}'")
    )
    op.execute(sa.text("DROP TYPE media_request_status"))
    op.execute(sa.text(f"CREATE TYPE media_request_status AS ENUM ({allowed})"))
    op.execute(
        sa.text(
            "ALTER TABLE media_requests ALTER COLUMN status TYPE media_request_status "
            "USING status::media_request_status"
        )
    )
