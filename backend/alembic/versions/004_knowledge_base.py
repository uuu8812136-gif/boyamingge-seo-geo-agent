"""knowledge base

Revision ID: 004
Revises: 003
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("doc_type", sa.String(32), nullable=False, server_default="general"),
        sa.Column("city", sa.String(64), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source", sa.String(512), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_knowledge_document_title", "knowledge_document", ["title"])
    op.create_index("ix_knowledge_document_doc_type", "knowledge_document", ["doc_type"])
    op.create_index("ix_knowledge_document_city", "knowledge_document", ["city"])
    op.create_index("ix_knowledge_document_category", "knowledge_document", ["category"])
    op.create_index("ix_knowledge_document_status", "knowledge_document", ["status"])

    op.create_table(
        "knowledge_chunk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("keywords", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_knowledge_chunk_document_id", "knowledge_chunk", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunk_document_id", table_name="knowledge_chunk")
    op.drop_table("knowledge_chunk")
    op.drop_index("ix_knowledge_document_status", table_name="knowledge_document")
    op.drop_index("ix_knowledge_document_category", table_name="knowledge_document")
    op.drop_index("ix_knowledge_document_city", table_name="knowledge_document")
    op.drop_index("ix_knowledge_document_doc_type", table_name="knowledge_document")
    op.drop_index("ix_knowledge_document_title", table_name="knowledge_document")
    op.drop_table("knowledge_document")
