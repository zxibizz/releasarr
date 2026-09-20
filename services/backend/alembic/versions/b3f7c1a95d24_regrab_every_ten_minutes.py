"""Run the re-grab sweep every ten minutes.

The interval is only a seed: `SqlAlchemyScheduledTaskRepository.register` writes
it on first registration and an existing row keeps whatever it holds, so lowering
`DEFAULT_INTERVALS` alone would leave every install that has already registered
the task running the old hourly schedule.

Only the previous default is moved. An interval an operator set themselves is
indistinguishable from the seed, but changing the default is not a reason to
overwrite someone's own choice.

Revision ID: b3f7c1a95d24
Revises: c81d4a7f2b90
Create Date: 2026-09-20 14:05:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b3f7c1a95d24"
down_revision = "c81d4a7f2b90"
branch_labels = None
depends_on = None

PREVIOUS_INTERVAL_SECONDS = 3600
INTERVAL_SECONDS = 600


def upgrade() -> None:
    """Move the seeded re-grab interval onto the new default."""

    op.execute(
        sa.text(
            "UPDATE scheduled_tasks SET interval_seconds = :interval "
            "WHERE kind = 'regrab' AND interval_seconds = :previous"
        ).bindparams(interval=INTERVAL_SECONDS, previous=PREVIOUS_INTERVAL_SECONDS)
    )


def downgrade() -> None:
    """Put an untouched re-grab interval back to the hourly default."""

    op.execute(
        sa.text(
            "UPDATE scheduled_tasks SET interval_seconds = :previous "
            "WHERE kind = 'regrab' AND interval_seconds = :interval"
        ).bindparams(interval=INTERVAL_SECONDS, previous=PREVIOUS_INTERVAL_SECONDS)
    )
