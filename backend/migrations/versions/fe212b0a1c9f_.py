"""empty message

Revision ID: fe212b0a1c9f
Revises: 0f993b96ef40
Create Date: 2024-09-20 19:18:48.115738

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fe212b0a1c9f"
down_revision: Union[str, None] = "0f993b96ef40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "release",
        sa.Column(
            "torrent_is_finished", sa.Boolean(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "release",
        sa.Column(
            "torrent_stats_raw",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
            server_default=None,
        ),
    )
    op.add_column(
        "release",
        sa.Column(
            "last_exported_torrent_guid",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
            server_default=None,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("release", "last_exported_torrent_guid")
    op.drop_column("release", "torrent_stats_raw")
    op.drop_column("release", "torrent_is_finished")
    # ### end Alembic commands ###
