"""add the re-grab file warning codes

Revision ID: d4b8c1f60a72
Revises: e5b3c7d9a1f2
Create Date: 2026-09-16 09:20:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd4b8c1f60a72'
down_revision = 'e5b3c7d9a1f2'
branch_labels = None
depends_on = None

OLD_CODES = ('mapping_overlap', 'regrab_indexer_unavailable', 'release_not_listed')
NEW_CODES = ('regrab_files_unmapped', 'regrab_files_missing')


def upgrade() -> None:
    # SQLite stores this enum as plain VARCHAR, so only PostgreSQL's native ENUM
    # type needs the new labels.
    if op.get_bind().dialect.name != "postgresql":
        return

    for code in NEW_CODES:
        op.execute(sa.text(f"ALTER TYPE request_warning_code ADD VALUE IF NOT EXISTS '{code}'"))


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    # PostgreSQL cannot remove an ENUM label in place, so the column is parked on
    # ``text`` while the type is recreated without them. Rows naming either code
    # cannot be cast back, and the next re-grab check re-derives them anyway.
    allowed = ", ".join(f"'{code}'" for code in OLD_CODES)

    op.execute(
        sa.text("ALTER TABLE request_warnings ALTER COLUMN code TYPE text USING code::text")
    )
    op.execute(sa.text(f"DELETE FROM request_warnings WHERE code NOT IN ({allowed})"))
    op.execute(sa.text("DROP TYPE request_warning_code"))
    op.execute(sa.text(f"CREATE TYPE request_warning_code AS ENUM ({allowed})"))
    op.execute(
        sa.text(
            "ALTER TABLE request_warnings ALTER COLUMN code TYPE request_warning_code "
            "USING code::request_warning_code"
        )
    )
