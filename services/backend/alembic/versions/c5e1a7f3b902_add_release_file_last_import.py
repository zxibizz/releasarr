"""add release_files last import columns

Revision ID: c5e1a7f3b902
Revises: a4d9e2f7c613
Create Date: 2026-11-13 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c5e1a7f3b902'
down_revision = 'a4d9e2f7c613'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('release_files', sa.Column('imported_target_id', sa.Integer(), nullable=True))
    op.add_column('release_files', sa.Column('imported_arr_file_id', sa.Integer(), nullable=True))
    op.add_column('release_files', sa.Column('imported_size_bytes', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('release_files', 'imported_size_bytes')
    op.drop_column('release_files', 'imported_arr_file_id')
    op.drop_column('release_files', 'imported_target_id')
