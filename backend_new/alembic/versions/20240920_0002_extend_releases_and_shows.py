"""Extend release model and add show entities

Revision ID: 20240920_0002
Revises: 20240920_0001
Create Date: 2025-09-20 09:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = "20240920_0002"
down_revision = "20240920_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "shows" not in inspector.get_table_names():
        op.create_table(
            "shows",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("sonarr_id", sa.Integer(), unique=True, nullable=True),
            sa.Column("tvdb_id", sa.Integer(), nullable=True),
            sa.Column("sonarr_data", sa.JSON(), nullable=True),
            sa.Column("tvdb_data", sa.JSON(), nullable=True),
            sa.Column("prowlarr_data", sa.JSON(), nullable=True),
            sa.Column("prowlarr_search", sa.String(length=255), nullable=True),
            sa.Column("is_missing", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("missing_seasons", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now(),
            ),
        )

    existing_columns = {col["name"] for col in inspector.get_columns("releases")}
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("releases")}

    with op.batch_alter_table("releases") as batch_op:
        if "search" not in existing_columns:
            batch_op.add_column(sa.Column("search", sa.String(length=255), nullable=True))
        if "prowlarr_guid" not in existing_columns:
            batch_op.add_column(sa.Column("prowlarr_guid", sa.String(length=255), nullable=True))
        if "prowlarr_data" not in existing_columns:
            batch_op.add_column(sa.Column("prowlarr_data", sa.JSON(), nullable=True))
        if "qbittorrent_guid" not in existing_columns:
            batch_op.add_column(sa.Column("qbittorrent_guid", sa.String(length=128), nullable=True))
        if "qbittorrent_data" not in existing_columns:
            batch_op.add_column(sa.Column("qbittorrent_data", sa.JSON(), nullable=True))
        if "torrent_stats" not in existing_columns:
            batch_op.add_column(sa.Column("torrent_stats", sa.JSON(), nullable=True))
        if "updated_at" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                    server_default=sa.func.now(),
                )
            )
        if "torrent_is_finished" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "torrent_is_finished",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
        if "last_imported_files_hash" not in existing_columns:
            batch_op.add_column(
                sa.Column("last_imported_files_hash", sa.String(length=128), nullable=True)
            )
        if "last_exported_torrent_guid" not in existing_columns:
            batch_op.add_column(
                sa.Column("last_exported_torrent_guid", sa.String(length=128), nullable=True)
            )
        if "export_failures_count" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "export_failures_count",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )
        if "show_id" not in existing_columns:
            batch_op.add_column(sa.Column("show_id", sa.Integer(), nullable=True))
        if "fk_releases_show_id" not in existing_fks:
            batch_op.create_foreign_key(
                "fk_releases_show_id",
                "shows",
                ["show_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "release_file_matchings" not in inspector.get_table_names():
        op.create_table(
            "release_file_matchings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("release_id", sa.Integer(), nullable=False),
            sa.Column("show_id", sa.Integer(), nullable=True),
            sa.Column("file_name", sa.String(length=1024), nullable=False),
            sa.Column("season_number", sa.Integer(), nullable=True),
            sa.Column("episode_number", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["release_id"], ["releases.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["show_id"], ["shows.id"], ondelete="SET NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "release_file_matchings" in inspector.get_table_names():
        op.drop_table("release_file_matchings")

    existing_columns = {col["name"] for col in inspector.get_columns("releases")}
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("releases")}

    with op.batch_alter_table("releases") as batch_op:
        if "fk_releases_show_id" in existing_fks:
            batch_op.drop_constraint("fk_releases_show_id", type_="foreignkey")
        for column in [
            "show_id",
            "export_failures_count",
            "last_exported_torrent_guid",
            "last_imported_files_hash",
            "torrent_is_finished",
            "torrent_stats",
            "qbittorrent_data",
            "qbittorrent_guid",
            "prowlarr_data",
            "prowlarr_guid",
            "search",
            "updated_at",
        ]:
            if column in existing_columns:
                batch_op.drop_column(column)

    if "shows" in inspector.get_table_names():
        op.drop_table("shows")
