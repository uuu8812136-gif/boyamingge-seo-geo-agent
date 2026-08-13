"""Add publish_artifact table for external publish screenshots/snapshots

Revision ID: 008
Revises: 007
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publish_artifact",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False, server_default="screenshot"),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_publish_artifact_task_id", "publish_artifact", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_publish_artifact_task_id", table_name="publish_artifact")
    op.drop_table("publish_artifact")
