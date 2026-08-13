"""user dealer_code

Revision ID: 003
Revises: 002
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("dealer_code", sa.String(32), nullable=True),
    )
    op.create_index("ix_user_dealer_code", "user", ["dealer_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_dealer_code", table_name="user")
    op.drop_column("user", "dealer_code")
