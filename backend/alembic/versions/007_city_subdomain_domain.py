"""Add subdomain/domain/seo fields to city, store; scope fields to user; attribution fields to lead

Revision ID: 007
Revises: 006
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── city 扩展：二级域名 / SEO / 内容状态 ──
    op.add_column("city", sa.Column("subdomain", sa.String(64), nullable=True))
    op.add_column("city", sa.Column("custom_domain", sa.String(255), nullable=True))
    op.add_column("city", sa.Column("canonical_url", sa.String(255), nullable=True))
    op.add_column("city", sa.Column("seo_keywords", JSONB, nullable=False, server_default="[]"))
    op.add_column("city", sa.Column("seo_indexable", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("city", sa.Column("robots_policy", sa.String(32), nullable=False, server_default="index_follow"))
    op.add_column("city", sa.Column("hero_image", sa.String(512), nullable=True))
    op.add_column("city", sa.Column("service_area_json", JSONB, nullable=False, server_default="[]"))
    op.add_column("city", sa.Column("service_tags", JSONB, nullable=False, server_default="[]"))
    op.add_column("city", sa.Column("content_status", sa.String(32), nullable=False, server_default="draft"))
    op.add_column("city", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("city", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_city_subdomain", "city", ["subdomain"], unique=True)
    op.create_index("ix_city_custom_domain", "city", ["custom_domain"], unique=True)

    # ── store 扩展：门店代码 / 主门店 / 预订 ──
    op.add_column("store", sa.Column("store_code", sa.String(64), nullable=True))
    op.add_column("store", sa.Column("manager_user_id", sa.Integer, nullable=True))
    op.add_column("store", sa.Column("dealer_code", sa.String(32), nullable=True))
    op.add_column("store", sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("store", sa.Column("booking_url", sa.String(512), nullable=True))
    op.add_column("store", sa.Column("wechat_qr", sa.String(512), nullable=True))
    op.add_column("store", sa.Column("gallery", JSONB, nullable=False, server_default="[]"))
    op.add_column("store", sa.Column("service_radius", sa.String(128), nullable=True))
    op.add_column("store", sa.Column("status", sa.String(32), nullable=False, server_default="active"))
    op.create_index("ix_store_store_code", "store", ["store_code"], unique=True)
    op.create_index("ix_store_manager_user_id", "store", ["manager_user_id"])
    op.create_index("ix_store_dealer_code", "store", ["dealer_code"])

    # ── user 扩展：城市/门店权限范围 ──
    op.add_column("user", sa.Column("city_id", sa.Integer, nullable=True))
    op.add_column("user", sa.Column("store_id", sa.Integer, nullable=True))
    op.add_column("user", sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("user", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_user_city_id", "user", ["city_id"])
    op.create_index("ix_user_store_id", "user", ["store_id"])

    # ── lead 扩展：二级域名归因 ──
    op.add_column("lead", sa.Column("city_id", sa.Integer, nullable=True))
    op.add_column("lead", sa.Column("store_id", sa.Integer, nullable=True))
    op.add_column("lead", sa.Column("host", sa.String(255), nullable=True))
    op.add_column("lead", sa.Column("source_path", sa.String(512), nullable=True))
    op.add_column("lead", sa.Column("landing_url", sa.String(512), nullable=True))
    op.add_column("lead", sa.Column("utm_json", JSONB, nullable=True))
    op.add_column("lead", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_lead_city_id", "lead", ["city_id"])
    op.create_index("ix_lead_store_id", "lead", ["store_id"])

    # ── 数据回填：已有 has_store 城市的 subdomain 默认等于 slug，并标记为 published ──
    op.execute(
        "UPDATE city SET subdomain = slug, content_status = 'published', published_at = NOW() "
        "WHERE has_store = true AND subdomain IS NULL"
    )
    # 主门店回填：每个城市 sort_order 最小的 active 门店设为主门店
    op.execute(
        "UPDATE store SET is_primary = true "
        "WHERE id IN (SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY city_id ORDER BY sort_order ASC) AS rn FROM store WHERE is_active = true) t WHERE rn = 1)"
    )


def downgrade() -> None:
    op.drop_index("ix_lead_store_id", table_name="lead")
    op.drop_index("ix_lead_city_id", table_name="lead")
    op.drop_column("lead", "assigned_at")
    op.drop_column("lead", "utm_json")
    op.drop_column("lead", "landing_url")
    op.drop_column("lead", "source_path")
    op.drop_column("lead", "host")
    op.drop_column("lead", "store_id")
    op.drop_column("lead", "city_id")

    op.drop_index("ix_user_store_id", table_name="user")
    op.drop_index("ix_user_city_id", table_name="user")
    op.drop_column("user", "last_login_at")
    op.drop_column("user", "is_active")
    op.drop_column("user", "store_id")
    op.drop_column("user", "city_id")

    op.drop_index("ix_store_dealer_code", table_name="store")
    op.drop_index("ix_store_manager_user_id", table_name="store")
    op.drop_index("ix_store_store_code", table_name="store")
    op.drop_column("store", "status")
    op.drop_column("store", "service_radius")
    op.drop_column("store", "gallery")
    op.drop_column("store", "wechat_qr")
    op.drop_column("store", "booking_url")
    op.drop_column("store", "is_primary")
    op.drop_column("store", "dealer_code")
    op.drop_column("store", "manager_user_id")
    op.drop_column("store", "store_code")

    op.drop_index("ix_city_custom_domain", table_name="city")
    op.drop_index("ix_city_subdomain", table_name="city")
    op.drop_column("city", "updated_at")
    op.drop_column("city", "published_at")
    op.drop_column("city", "content_status")
    op.drop_column("city", "service_tags")
    op.drop_column("city", "service_area_json")
    op.drop_column("city", "hero_image")
    op.drop_column("city", "robots_policy")
    op.drop_column("city", "seo_indexable")
    op.drop_column("city", "seo_keywords")
    op.drop_column("city", "canonical_url")
    op.drop_column("city", "custom_domain")
    op.drop_column("city", "subdomain")
