"""Add stock_splits table

Revision ID: a1b2c3d4e5f6
Revises: df3c33605d6e
Create Date: 2026-06-29

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "df3c33605d6e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stock_splits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker_symbol", sa.String(length=20), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("ratio", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ticker_symbol", "effective_date", name="uix_split_ticker_date"
        ),
    )
    with op.batch_alter_table("stock_splits", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_stock_splits_ticker_symbol"),
            ["ticker_symbol"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("stock_splits", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_stock_splits_ticker_symbol"))

    op.drop_table("stock_splits")
