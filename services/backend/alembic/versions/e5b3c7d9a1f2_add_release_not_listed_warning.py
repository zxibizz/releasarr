"""add release_not_listed request warning code

Revision ID: e5b3c7d9a1f2
Revises: dfed8040c181
Create Date: 2026-09-15 14:10:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e5b3c7d9a1f2'
down_revision = 'dfed8040c181'
branch_labels = None
depends_on = None

OLD_CODES = ('mapping_overlap', 'regrab_indexer_unavailable')
NEW_CODE = 'release_not_listed'


def upgrade() -> None:
    # SQLite stores this enum as plain VARCHAR, so only PostgreSQL's native ENUM
    # type needs the new label.
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(sa.text(f"ALTER TYPE request_warning_code ADD VALUE IF NOT EXISTS '{NEW_CODE}'"))


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    # PostgreSQL cannot remove an ENUM label in place, so the column is parked on
    # ``text`` while the type is recreated without it. Rows naming the new code
    # cannot be cast back, and the next regrab check re-derives them from the
    # indexer anyway.
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
