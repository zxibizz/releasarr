"""Drop can_impersonate from service_api_keys.

Impersonation is now derived from the bound user's role (admin) instead of a
separate per-key flag.

Revision ID: 5b6c7d8e9f0a
Revises: 4f6a7b8c9d0e
Create Date: 2026-09-14 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5b6c7d8e9f0a"
down_revision = "4f6a7b8c9d0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("service_api_keys", "can_impersonate")


def downgrade() -> None:
    op.add_column(
        "service_api_keys",
        sa.Column(
            "can_impersonate", sa.Boolean(), server_default="0", nullable=False
        ),
    )
