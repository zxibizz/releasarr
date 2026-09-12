"""add scheduled tasks and per-task sync jobs

Revision ID: c58f2a91d374
Revises: b7d4c91e2f08
Create Date: 2026-09-12 15:08:42.119874

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c58f2a91d374'
down_revision = 'b7d4c91e2f08'
branch_labels = None
depends_on = None

SYNC_JOB_KINDS = ('sonarr_sync', 'release_sync', 'export', 'regrab')
OLD_SYNC_JOB_KINDS = ('downloads', 'full')


def upgrade() -> None:
    # Jobs are now one task each rather than a bundle, so the previous 'full' and
    # 'downloads' rows no longer describe anything runnable.
    op.execute(sa.text("DELETE FROM sync_jobs"))

    with op.batch_alter_table('sync_jobs') as batch_op:
        batch_op.alter_column(
            'kind',
            existing_type=sa.Enum(*OLD_SYNC_JOB_KINDS, name='sync_job_kind'),
            type_=sa.Enum(*SYNC_JOB_KINDS, name='sync_job_kind'),
            existing_nullable=False,
        )

    op.create_table('scheduled_tasks',
    sa.Column('kind', sa.Enum(*SYNC_JOB_KINDS, name='scheduled_task_kind'), nullable=False),
    sa.Column('interval_seconds', sa.Integer(), nullable=False),
    sa.Column('last_execution', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_duration_ms', sa.Integer(), nullable=True),
    sa.Column('last_status', sa.Enum('queued', 'running', 'completed', 'failed', name='scheduled_task_status'), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('kind')
    )


def downgrade() -> None:
    op.drop_table('scheduled_tasks')

    op.execute(sa.text("DELETE FROM sync_jobs"))

    with op.batch_alter_table('sync_jobs') as batch_op:
        batch_op.alter_column(
            'kind',
            existing_type=sa.Enum(*SYNC_JOB_KINDS, name='sync_job_kind'),
            type_=sa.Enum(*OLD_SYNC_JOB_KINDS, name='sync_job_kind'),
            existing_nullable=False,
        )
