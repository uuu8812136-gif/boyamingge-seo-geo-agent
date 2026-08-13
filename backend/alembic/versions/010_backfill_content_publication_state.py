"""Backfill legacy content metadata and publication state.

Revision ID: 010
Revises: 009
Create Date: 2026-07-15
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def _title_from_markdown(markdown: str | None, content_id: int) -> str:
    for line in (markdown or "").splitlines():
        candidate = re.sub(r"^#{1,6}\s*", "", line).strip()
        if candidate:
            return candidate[:500]
    return f"内容 {content_id}"


def _slug_from_title(title: str, content_id: int) -> str:
    ascii_slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()[:220]
    return ascii_slug or f"post-{content_id}"


def upgrade() -> None:
    bind = op.get_bind()
    contents = bind.execute(
        text("SELECT id, title, slug, markdown, status, published_at FROM content ORDER BY id")
    ).mappings().all()
    publications = bind.execute(
        text(
            "SELECT id, content_id, url, published_at, created_at "
            "FROM publication WHERE platform = 'website' AND status = 'published' "
            "ORDER BY content_id, id DESC"
        )
    ).mappings().all()

    latest_publication: dict[int, dict] = {}
    duplicate_ids: list[int] = []
    for row in publications:
        content_id = int(row["content_id"])
        if content_id in latest_publication:
            duplicate_ids.append(int(row["id"]))
        else:
            latest_publication[content_id] = dict(row)

    if duplicate_ids:
        bind.execute(
            text("UPDATE publication SET status = 'offline' WHERE id IN :ids").bindparams(
                ids=tuple(duplicate_ids), expanding=True
            )
        )

    used_slugs = {str(row["slug"]) for row in contents if row["slug"]}
    for row in contents:
        content_id = int(row["id"])
        title = str(row["title"] or "").strip() or _title_from_markdown(row["markdown"], content_id)
        slug = str(row["slug"] or "").strip()
        if not slug:
            base = _slug_from_title(title, content_id)
            slug = base
            suffix = 2
            while slug in used_slugs:
                slug = f"{base}-{suffix}"
                suffix += 1
            used_slugs.add(slug)

        values: dict[str, object] = {"id": content_id, "title": title, "slug": slug}
        assignment = "title = :title, slug = :slug"
        published = latest_publication.get(content_id)
        if published:
            published_at = published.get("published_at") or published.get("created_at") or datetime.now(timezone.utc)
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except ValueError:
                    published_at = datetime.now(timezone.utc)
            values["published_at"] = published_at
            assignment += ", status = 'published', published_at = :published_at, offline_at = NULL"
        bind.execute(text(f"UPDATE content SET {assignment} WHERE id = :id"), values)

    op.create_index(
        "uq_publication_one_live_website",
        "publication",
        ["content_id", "platform"],
        unique=True,
        postgresql_where=text("platform = 'website' AND status = 'published'"),
        sqlite_where=text("platform = 'website' AND status = 'published'"),
    )


def downgrade() -> None:
    op.drop_index("uq_publication_one_live_website", table_name="publication")
