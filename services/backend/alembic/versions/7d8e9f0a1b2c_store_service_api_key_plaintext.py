"""Store the service API key in plaintext, not hashed, and drop the prefix.

It isn't a password: an admin needs to read it back to configure whatever
integration uses it, the same as Sonarr and Radarr's own API keys. Existing
hashes can't be recovered as plaintext, so any current key is discarded; it
will be regenerated the next time it's requested.

Revision ID: 7d8e9f0a1b2c
Revises: 6c7d8e9f0a1b
Create Date: 2026-09-14 14:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7d8e9f0a1b2c"
down_revision = "6c7d8e9f0a1b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM service_api_keys")
    with op.batch_alter_table("service_api_keys", schema=None, recreate="always") as batch_op:
        batch_op.drop_column("prefix")
        batch_op.alter_column("key_hash", new_column_name="key")


def downgrade() -> None:
    op.execute("DELETE FROM service_api_keys")
    with op.batch_alter_table("service_api_keys", schema=None, recreate="always") as batch_op:
        batch_op.alter_column("key", new_column_name="key_hash")
        batch_op.add_column(sa.Column("prefix", sa.String(length=12), nullable=False, server_default=""))
