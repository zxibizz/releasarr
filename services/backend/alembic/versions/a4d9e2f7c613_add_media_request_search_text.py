"""add media_requests.search_text

Revision ID: a4d9e2f7c613
Revises: f8c2d6a4b1e9
Create Date: 2026-11-08 18:00:00.000000

"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a4d9e2f7c613"
down_revision = "f8c2d6a4b1e9"
branch_labels = None
depends_on = None


# A frozen copy of `fold_search_text` and its listener: the backfill has to produce what
# the application would have written, whatever that code later becomes.
def _fold(text: str) -> str:
    return text.casefold().replace("\u0451", "\u0435")


def _search_text(title: str | None, series_title: str | None, localizations: object) -> str:
    if isinstance(localizations, str):
        localizations = json.loads(localizations)
    titles = [title, series_title]
    if isinstance(localizations, dict):
        titles.extend(
            value.get("title") for value in localizations.values() if isinstance(value, dict)
        )
    return "\n".join(_fold(value) for value in titles if value)


def upgrade() -> None:
    op.add_column(
        "media_requests",
        sa.Column("search_text", sa.Text(), server_default="", nullable=False),
    )

    media_requests = sa.table(
        "media_requests",
        sa.column("id", sa.String()),
        sa.column("title", sa.String()),
        sa.column("series_title", sa.String()),
        sa.column("localizations", sa.JSON()),
        sa.column("search_text", sa.Text()),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            media_requests.c.id,
            media_requests.c.title,
            media_requests.c.series_title,
            media_requests.c.localizations,
        )
    ).all()
    for row in rows:
        bind.execute(
            media_requests.update()
            .where(media_requests.c.id == row.id)
            .values(search_text=_search_text(row.title, row.series_title, row.localizations))
        )


def downgrade() -> None:
    op.drop_column("media_requests", "search_text")
