"""Add content and publication fields used by admin pages

Revision ID: 009
Revises: 008
Create Date: 2026-07-07
"""
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS post_type VARCHAR(16) NOT NULL DEFAULT 'article'")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS title VARCHAR(500)")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS slug VARCHAR(300)")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS summary VARCHAR(1000)")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS cover_image VARCHAR(512)")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS cover_image_alt VARCHAR(255)")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS seo_title VARCHAR(200)")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS seo_description VARCHAR(500)")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS canonical VARCHAR(512)")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS keywords JSONB NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS store_id INTEGER")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS author_id INTEGER")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS offline_at TIMESTAMPTZ")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_post_type ON content(post_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_slug ON content(slug)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_store_id ON content(store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_scheduled_at ON content(scheduled_at)")

    op.execute("ALTER TABLE publication ADD COLUMN IF NOT EXISTS publish_mode VARCHAR(16) NOT NULL DEFAULT 'direct'")
    op.execute("ALTER TABLE publication ADD COLUMN IF NOT EXISTS operator_id INTEGER")
    op.execute("ALTER TABLE publication ADD COLUMN IF NOT EXISTS error_message TEXT")
    op.execute("ALTER TABLE publication ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
    op.execute("ALTER TABLE publication ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
    op.execute("CREATE INDEX IF NOT EXISTS ix_publication_content_id ON publication(content_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_publication_status ON publication(status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_publication_status")
    op.execute("DROP INDEX IF EXISTS ix_publication_content_id")
    op.execute("ALTER TABLE publication DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE publication DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE publication DROP COLUMN IF EXISTS error_message")
    op.execute("ALTER TABLE publication DROP COLUMN IF EXISTS operator_id")
    op.execute("ALTER TABLE publication DROP COLUMN IF EXISTS publish_mode")

    op.execute("DROP INDEX IF EXISTS ix_content_scheduled_at")
    op.execute("DROP INDEX IF EXISTS ix_content_store_id")
    op.execute("DROP INDEX IF EXISTS ix_content_slug")
    op.execute("DROP INDEX IF EXISTS ix_content_post_type")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS offline_at")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS published_at")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS scheduled_at")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS author_id")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS store_id")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS keywords")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS canonical")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS seo_description")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS seo_title")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS cover_image_alt")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS cover_image")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS summary")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS slug")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS title")
    op.execute("ALTER TABLE content DROP COLUMN IF EXISTS post_type")
