"""add release_files.ignored

Revision ID: f8c2d6a4b1e9
Revises: b3f7c1a95d24
Create Date: 2026-11-08 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f8c2d6a4b1e9'
down_revision = 'b3f7c1a95d24'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'release_files',
        sa.Column('ignored', sa.Boolean(), server_default='0', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('release_files', 'ignored')
