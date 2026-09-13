"""Widen the release columns fed by indexer and torrent metadata.

Revision ID: e1f36b8ac704
Revises: a4c7e2b91f56
Create Date: 2026-09-13 06:20:00.000000

``releases.name`` holds the tracker's own title, which on trackers that list
dubs, episode ranges and release notes in the title easily passes 255
characters, so grabbing such a release failed with
``StringDataRightTruncationError``. ``releases.id`` is the Prowlarr guid,
usually a forum URL, and the release file name and path come from the torrent's
file list; all of them are unbounded upstream and were sized by guesswork.

SQLite ignores VARCHAR lengths, so it never hit the limit and has nothing to
migrate; rebuilding ``releases`` there would also have to be threaded through
the two tables referencing its primary key.

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e1f36b8ac704'
down_revision = 'a4c7e2b91f56'
branch_labels = None
depends_on = None

# Column type changes as (table, column, widened type, original type).
COLUMNS = (
    ("releases", "id", "varchar(512)", "varchar(64)"),
    ("release_request_links", "release_id", "varchar(512)", "varchar(64)"),
    ("release_files", "release_id", "varchar(512)", "varchar(64)"),
    ("releases", "name", "text", "varchar(255)"),
    ("release_files", "name", "text", "varchar(255)"),
    ("release_files", "path", "text", "varchar(1024)"),
)


def _alter_types(widen: bool) -> None:
    for table, column, widened, original in COLUMNS:
        target = widened if widen else original
        op.execute(
            sa.text(f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE {target}')
        )


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    _alter_types(widen=True)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    # Narrowing fails on any row that already exceeds the original limits.
    _alter_types(widen=False)
