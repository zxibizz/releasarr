"""Initial schema

Revision ID: 20240920_0001
Revises:
Create Date: 2025-09-20 08:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20240920_0001"
down_revision = None
branch_labels = None
depends_on = None


request_type_enum = sa.Enum("movie", "series", name="requesttype")
request_status_enum = sa.Enum(
    "pending", "searching", "downloading", "completed", "failed", name="requeststatus"
)


def upgrade() -> None:
    request_type_enum.create(op.get_bind(), checkfirst=True)
    request_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(length=64), nullable=True, unique=True),
        sa.Column("type", request_type_enum, nullable=False),
        sa.Column("status", request_status_enum, nullable=False, server_default="pending"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("poster_url", sa.String(length=500), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("genres", sa.Text(), nullable=True),
        sa.Column("imdb_id", sa.String(length=64), nullable=True),
        sa.Column("runtime", sa.Integer(), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("total_episodes", sa.Integer(), nullable=True),
        sa.Column("series_title", sa.String(length=255), nullable=True),
        sa.Column("series_year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "releases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(length=64), nullable=True, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("hash", sa.String(length=128), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("download_speed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("upload_speed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("seeders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leechers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("added_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("torrent_source", sa.String(length=128), nullable=True),
        sa.Column("quality", sa.String(length=64), nullable=True),
    )

    op.create_table(
        "release_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("total_releases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_downloads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_releases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_uploaded", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_downloaded", sa.BigInteger(), nullable=False, server_default="0"),
    )

    op.create_table(
        "release_files",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("release_id", sa.Integer(), sa.ForeignKey("releases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("episode", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("requests.id"), nullable=True),
    )

    op.create_table(
        "release_requests",
        sa.Column("release_id", sa.Integer(), sa.ForeignKey("releases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("requests.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("release_requests")
    op.drop_table("release_files")
    op.drop_table("release_stats")
    op.drop_table("releases")
    op.drop_table("requests")
    request_status_enum.drop(op.get_bind(), checkfirst=True)
    request_type_enum.drop(op.get_bind(), checkfirst=True)
