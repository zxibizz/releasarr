"""repair sync_job_kind enum labels on postgresql

Revision ID: d3e9a17c5b42
Revises: c58f2a91d374
Create Date: 2026-09-12 20:35:00.000000

Revision c58f2a91d374 replaced the ``sync_job_kind`` labels ('downloads', 'full')
with the per-task kinds using ``batch_alter_table``. On SQLite that recreates the
table together with its CHECK constraint, so the new labels took effect. On
PostgreSQL batch mode falls through to a plain
``ALTER TABLE sync_jobs ALTER COLUMN kind TYPE sync_job_kind``, which casts the
column to the type it already has and never touches the ENUM's labels. The type
kept only 'downloads' and 'full', so any statement mentioning a current kind
failed with ``InvalidTextRepresentationError: invalid input value for enum
sync_job_kind: "sonarr_sync"``.

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd3e9a17c5b42'
down_revision = 'c58f2a91d374'
branch_labels = None
depends_on = None

SYNC_JOB_KINDS = ('sonarr_sync', 'release_sync', 'export', 'regrab')
OLD_SYNC_JOB_KINDS = ('downloads', 'full')


def _rebuild_kind_enum(labels: tuple[str, ...]) -> None:
    """Replace the sync_job_kind ENUM with one holding exactly ``labels``.

    PostgreSQL cannot remove ENUM labels in place, so the column is parked on
    ``text`` while the type is recreated. ``sync_jobs`` is the queue hand-off
    between the API and the scheduler and ``kind`` carries no server default,
    so nothing else has to be preserved across the swap.
    """

    allowed = ", ".join(f"'{label}'" for label in labels)

    op.execute(sa.text("ALTER TABLE sync_jobs ALTER COLUMN kind TYPE text USING kind::text"))
    # Queued rows naming a kind outside the target set could not be cast back.
    op.execute(sa.text(f"DELETE FROM sync_jobs WHERE kind NOT IN ({allowed})"))
    op.execute(sa.text("DROP TYPE sync_job_kind"))
    op.execute(sa.text(f"CREATE TYPE sync_job_kind AS ENUM ({allowed})"))
    op.execute(
        sa.text(
            "ALTER TABLE sync_jobs ALTER COLUMN kind TYPE sync_job_kind "
            "USING kind::sync_job_kind"
        )
    )


def upgrade() -> None:
    # SQLite already picked the new labels up when c58f2a91d374 rebuilt the table.
    if op.get_bind().dialect.name != "postgresql":
        return

    _rebuild_kind_enum(SYNC_JOB_KINDS)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    _rebuild_kind_enum(OLD_SYNC_JOB_KINDS)
