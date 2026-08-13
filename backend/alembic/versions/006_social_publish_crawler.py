"""Add social publish and crawler tables

Revision ID: 006
Revises: 005
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_account",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("platform_code", sa.Integer, nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("internal_account_id", sa.String(128), nullable=True),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("avatar", sa.String(512), nullable=True),
        sa.Column("cookie_status", sa.String(32), nullable=False, server_default="missing_cookie"),
        sa.Column("cookie_path", sa.String(512), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("city", sa.String(64), nullable=True),
        sa.Column("dealer_id", sa.String(32), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("raw", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_social_account_platform", "social_account", ["platform"])
    op.create_index("ix_social_account_internal_account_id", "social_account", ["internal_account_id"])
    op.create_index("ix_social_account_city", "social_account", ["city"])
    op.create_index("ix_social_account_dealer_id", "social_account", ["dealer_id"])

    op.create_table(
        "social_material",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("content_id", sa.Integer, nullable=True),
        sa.Column("dealer_id", sa.String(32), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("local_path", sa.String(512), nullable=False),
        sa.Column("internal_file_id", sa.String(128), nullable=True),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("size_mb", sa.Float, nullable=True),
        sa.Column("duration_sec", sa.Float, nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("cover_path", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_social_material_content_id", "social_material", ["content_id"])
    op.create_index("ix_social_material_dealer_id", "social_material", ["dealer_id"])
    op.create_index("ix_social_material_internal_file_id", "social_material", ["internal_file_id"])

    op.create_table(
        "social_publication_task",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("content_id", sa.Integer, nullable=False),
        sa.Column("publication_id", sa.Integer, nullable=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("platform_code", sa.Integer, nullable=False),
        sa.Column("social_account_id", sa.Integer, nullable=False),
        sa.Column("social_material_id", sa.Integer, nullable=True),
        sa.Column("internal_file_id", sa.String(128), nullable=True),
        sa.Column("worker_task_id", sa.String(128), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("topics", JSONB, nullable=False, server_default="[]"),
        sa.Column("cover_path", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_response", JSONB, nullable=True),
        sa.Column("allow_duplicate", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("interval_seconds", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_social_publication_task_content_id", "social_publication_task", ["content_id"])
    op.create_index("ix_social_publication_task_publication_id", "social_publication_task", ["publication_id"])
    op.create_index("ix_social_publication_task_platform", "social_publication_task", ["platform"])
    op.create_index("ix_social_publication_task_social_account_id", "social_publication_task", ["social_account_id"])
    op.create_index("ix_social_publication_task_status", "social_publication_task", ["status"])

    op.create_table(
        "social_publish_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, nullable=False),
        sa.Column("level", sa.String(16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_social_publish_log_task_id", "social_publish_log", ["task_id"])

    op.create_table(
        "social_crawler_job",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("crawler_type", sa.String(16), nullable=False, server_default="search"),
        sa.Column("keyword", sa.String(255), nullable=True),
        sa.Column("account_ref", sa.String(255), nullable=True),
        sa.Column("city", sa.String(64), nullable=True),
        sa.Column("login_type", sa.String(16), nullable=False, server_default="cookie"),
        sa.Column("cookies", sa.Text, nullable=True),
        sa.Column("save_option", sa.String(16), nullable=False, server_default="jsonl"),
        sa.Column("max_notes_count", sa.Integer, nullable=False, server_default="20"),
        sa.Column("headless", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("save_path", sa.String(512), nullable=True),
        sa.Column("pid", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_social_crawler_job_platform", "social_crawler_job", ["platform"])
    op.create_index("ix_social_crawler_job_city", "social_crawler_job", ["city"])
    op.create_index("ix_social_crawler_job_status", "social_crawler_job", ["status"])

    op.create_table(
        "social_crawler_item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("source_keyword", sa.String(255), nullable=True),
        sa.Column("note_id", sa.String(128), nullable=True),
        sa.Column("author", sa.String(128), nullable=True),
        sa.Column("author_id", sa.String(128), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("publish_time", sa.String(64), nullable=True),
        sa.Column("likes", sa.Integer, nullable=True),
        sa.Column("comments", sa.Integer, nullable=True),
        sa.Column("collects", sa.Integer, nullable=True),
        sa.Column("shares", sa.Integer, nullable=True),
        sa.Column("city", sa.String(64), nullable=True),
        sa.Column("tag_list", JSONB, nullable=True),
        sa.Column("raw", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_social_crawler_item_job_id", "social_crawler_item", ["job_id"])
    op.create_index("ix_social_crawler_item_platform", "social_crawler_item", ["platform"])
    op.create_index("ix_social_crawler_item_source_keyword", "social_crawler_item", ["source_keyword"])
    op.create_index("ix_social_crawler_item_city", "social_crawler_item", ["city"])

    op.create_table(
        "social_crawler_import_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, nullable=True),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("platform", sa.String(32), nullable=True),
        sa.Column("imported_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_social_crawler_import_log_job_id", "social_crawler_import_log", ["job_id"])


def downgrade() -> None:
    op.drop_table("social_crawler_import_log")
    op.drop_table("social_crawler_item")
    op.drop_table("social_crawler_job")
    op.drop_table("social_publish_log")
    op.drop_table("social_publication_task")
    op.drop_table("social_material")
    op.drop_table("social_account")
