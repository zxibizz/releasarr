"""create sync jobs table

Revision ID: b7d4c91e2f08
Revises: 5a168e8321ab
Create Date: 2026-09-12 14:35:11.204518

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d4c91e2f08'
down_revision = '5a168e8321ab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('sync_jobs',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('kind', sa.Enum('downloads', 'full', name='sync_job_kind'), nullable=False),
    sa.Column('status', sa.Enum('queued', 'running', 'completed', 'failed', name='sync_job_status'), server_default='queued', nullable=False),
    sa.Column('trigger', sa.Enum('api', 'download_client', 'schedule', name='sync_job_trigger'), server_default='api', nullable=False),
    sa.Column('queued_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('result', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_jobs_status_queued_at', 'sync_jobs', ['status', 'queued_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_sync_jobs_status_queued_at', table_name='sync_jobs')
    op.drop_table('sync_jobs')
