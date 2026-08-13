"""Add city, store, city_case, city_faq tables

Revision ID: 005
Revises: 004
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "city",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("province", sa.String(32), nullable=False),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("has_store", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("seo_title", sa.String(200), nullable=True),
        sa.Column("seo_description", sa.String(500), nullable=True),
        sa.Column("hero_title", sa.String(200), nullable=True),
        sa.Column("hero_subtitle", sa.String(500), nullable=True),
    )
    op.create_index("ix_city_name", "city", ["name"])
    op.create_index("ix_city_slug", "city", ["slug"])

    op.create_table(
        "store",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("city_id", sa.Integer, sa.ForeignKey("city.id"), nullable=False, index=True),
        sa.Column("store_name", sa.String(128), nullable=False),
        sa.Column("province", sa.String(32), nullable=False),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("district", sa.String(64), nullable=False),
        sa.Column("address", sa.String(256), nullable=False),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("opening_hours", sa.String(128), nullable=True),
        sa.Column("services", JSONB, nullable=False, server_default="[]"),
        sa.Column("cover_image", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "city_case",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("city_id", sa.Integer, sa.ForeignKey("city.id"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("service_type", sa.String(64), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("images", JSONB, nullable=False, server_default="[]"),
    )

    op.create_table(
        "city_faq",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("city_id", sa.Integer, sa.ForeignKey("city.id"), nullable=False, index=True),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("city_faq")
    op.drop_table("city_case")
    op.drop_table("store")
    op.drop_table("city")
