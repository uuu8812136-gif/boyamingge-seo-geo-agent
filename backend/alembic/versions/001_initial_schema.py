"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "intent",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("intent_type", sa.String(32), nullable=False),
        sa.Column("city_list", postgresql.JSONB(), nullable=False),
        sa.Column("keyword_json", postgresql.JSONB(), nullable=False),
        sa.Column("hotness_score", sa.Integer(), nullable=False),
        sa.Column("difficulty_score", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(8), nullable=False),
    )
    op.create_table(
        "content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("intent_id", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("eeat_score", sa.Integer(), nullable=True),
        sa.Column("eeat_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("model_used", sa.String(64), nullable=True),
        sa.Column("schema_jsonld", sa.Text(), nullable=True),
    )
    op.create_table(
        "content_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("template_body", sa.Text(), nullable=False),
        sa.Column("similarity_threshold", sa.Float(), nullable=False),
    )
    op.create_table(
        "publication",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("tier", sa.String(4), nullable=False),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("published_at", sa.String(64), nullable=True),
        sa.Column("dealer_id", sa.String(32), nullable=True),
    )
    op.create_table(
        "dealer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("phone", sa.String(64), nullable=False),
        sa.Column("baijiahao_account", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("activation_score", sa.Integer(), nullable=False),
    )
    op.create_table(
        "lead",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("interest", sa.String(128), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("utm", sa.String(512), nullable=True),
        sa.Column("dealer_id", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_table(
        "call_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("call_id", sa.String(64), nullable=False, unique=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("result", sa.String(64), nullable=True),
        sa.Column("recording_url", sa.String(512), nullable=True),
    )
    op.create_table(
        "material",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dealer_id", sa.String(32), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("oss_url", sa.String(512), nullable=False),
        sa.Column("copyright_declared", sa.String(8), nullable=False),
        sa.Column("uploaded_at", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    for table in [
        "material",
        "call_record",
        "lead",
        "dealer",
        "publication",
        "content_template",
        "content",
        "intent",
        "user",
    ]:
        op.drop_table(table)
