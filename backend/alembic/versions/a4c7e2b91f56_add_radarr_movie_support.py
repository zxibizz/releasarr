"""Add Radarr linkage column and the radarr_sync task kind.

Revision ID: a4c7e2b91f56
Revises: d3e9a17c5b42
Create Date: 2026-09-12 23:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a4c7e2b91f56'
down_revision = 'd3e9a17c5b42'
branch_labels = None
depends_on = None

KIND_ENUMS = ("sync_job_kind", "scheduled_task_kind")
NEW_KIND = "radarr_sync"
OLD_SYNC_JOB_KINDS = ('sonarr_sync', 'release_sync', 'export', 'regrab')

# The two enums back one column each; ``scheduled_tasks.kind`` is also its
# primary key, so a row naming a dropped label has to go before the swap.
KIND_COLUMNS = {
    "sync_job_kind": ("sync_jobs", "kind"),
    "scheduled_task_kind": ("scheduled_tasks", "kind"),
}


def _rebuild_kind_enum(type_name: str, labels: tuple[str, ...]) -> None:
    """Replace ``type_name`` with an ENUM holding exactly ``labels``.

    PostgreSQL cannot remove ENUM labels in place, so the column is parked on
    ``text`` while the type is recreated. Neither column carries a server
    default, so nothing else has to be preserved across the swap.
    """

    table, column = KIND_COLUMNS[type_name]
    allowed = ", ".join(f"'{label}'" for label in labels)

    op.execute(
        sa.text(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE text '
            f'USING "{column}"::text'
        )
    )
    op.execute(sa.text(f'DELETE FROM {table} WHERE "{column}" NOT IN ({allowed})'))
    op.execute(sa.text(f"DROP TYPE {type_name}"))
    op.execute(sa.text(f"CREATE TYPE {type_name} AS ENUM ({allowed})"))
    op.execute(
        sa.text(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE {type_name} '
            f'USING "{column}"::{type_name}'
        )
    )


def upgrade() -> None:
    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("radarr_movie_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_media_requests_radarr_movie_id",
            ["radarr_movie_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_media_requests_radarr_movie",
            ["radarr_movie_id"],
        )

    # SQLite stores these enums as plain VARCHAR, so only PostgreSQL's native
    # ENUM types need the new label.
    if op.get_bind().dialect.name != "postgresql":
        return

    for type_name in KIND_ENUMS:
        op.execute(sa.text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{NEW_KIND}'"))


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for type_name in KIND_ENUMS:
            _rebuild_kind_enum(type_name, OLD_SYNC_JOB_KINDS)

    with op.batch_alter_table("media_requests", schema=None) as batch_op:
        batch_op.drop_constraint("uq_media_requests_radarr_movie", type_="unique")
        batch_op.drop_index("ix_media_requests_radarr_movie_id")
        batch_op.drop_column("radarr_movie_id")
