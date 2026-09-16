"""remove seeding release status

Revision ID: a8b9c0d1e2f3
Revises: 7a1f5c2e9d43
Create Date: 2026-09-16 12:00:00.000000

A seeding torrent is a completed download from releasarr's perspective, and the
state projection already returned ``completed`` for any finished torrent before
reaching the seeding branch. Rows still holding the label are folded into
``completed`` before the type is recreated without it.

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a8b9c0d1e2f3'
down_revision = '7a1f5c2e9d43'
branch_labels = None
depends_on = None

OLD_STATUSES = ('pending', 'downloading', 'seeding', 'completed', 'failed')
REMOVED_STATUS = 'seeding'


def upgrade() -> None:
    # SQLite stores this enum as plain VARCHAR, so only PostgreSQL's native ENUM
    # type needs the label dropped.
    if op.get_bind().dialect.name != "postgresql":
        return

    # PostgreSQL cannot remove an ENUM label in place, so the column is parked on
    # ``text`` while the type is recreated without it. Seeding releases were
    # finished downloads awaiting import, which is what ``completed`` means.
    allowed = ", ".join(f"'{label}'" for label in OLD_STATUSES if label != REMOVED_STATUS)

    op.execute(
        sa.text(
            "ALTER TABLE releases ALTER COLUMN status TYPE text USING status::text"
        )
    )
    op.execute(
        sa.text(
            f"UPDATE releases SET status = 'completed' WHERE status = '{REMOVED_STATUS}'"
        )
    )
    op.execute(sa.text("DROP TYPE release_status"))
    op.execute(sa.text(f"CREATE TYPE release_status AS ENUM ({allowed})"))
    op.execute(
        sa.text(
            "ALTER TABLE releases ALTER COLUMN status TYPE release_status "
            "USING status::release_status"
        )
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        sa.text(f"ALTER TYPE release_status ADD VALUE IF NOT EXISTS '{REMOVED_STATUS}'")
    )
