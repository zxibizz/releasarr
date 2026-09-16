"""add release missing_since

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-16 12:00:02.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'releases',
        sa.Column('missing_since', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('releases', 'missing_since')
