"""Add intel_snapshot and intel_correlation tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intel_snapshot",
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id"), primary_key=True),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("sample_count", sa.Integer()),
        sa.Column("rv_30d", sa.Numeric(8, 6)),
        sa.Column("rv_regime", sa.String(10)),
        sa.Column("price_mean_30d", sa.Numeric(20, 10)),
        sa.Column("price_stdev_30d", sa.Numeric(20, 10)),
        sa.Column("z_score", sa.Numeric(8, 4)),
        sa.Column("price_pctile_30d", sa.Numeric(5, 2)),
        sa.Column("spread_bps", sa.Numeric(10, 4)),
    )
    op.create_table(
        "intel_correlation",
        sa.Column("instrument_id_a", sa.Integer(), sa.ForeignKey("instruments.id"), primary_key=True),
        sa.Column("instrument_id_b", sa.Integer(), sa.ForeignKey("instruments.id"), primary_key=True),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("pearson_r", sa.Numeric(6, 4)),
        sa.Column("sample_count", sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table("intel_correlation")
    op.drop_table("intel_snapshot")
